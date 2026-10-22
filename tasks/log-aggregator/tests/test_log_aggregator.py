"""Grader for log-aggregator."""

from pathlib import Path

import pytest

from log_aggregator import aggregate, aggregate_file


def test_sample_file_summary():
    # logs/app.log ships with the task setup; the grader runs with the work dir as cwd.
    result = aggregate_file(Path("logs") / "app.log", top=3)
    assert result["total"] == 9
    assert result["malformed"] == 3
    assert result["by_level"] == {"INFO": 2, "DEBUG": 1, "ERROR": 4, "WARNING": 1, "CRITICAL": 1}
    assert result["by_hour"] == {"2026-03-01 09": 2, "2026-03-01 10": 5, "2026-03-01 11": 2}
    assert result["top_errors"] == [
        ["api", "upstream timeout", 2],
        ["db", "connection refused", 2],
        ["db", "disk full", 1],
    ]


def test_empty_input():
    assert aggregate([]) == {"total": 0, "malformed": 0, "by_level": {}, "by_hour": {}, "top_errors": []}


def test_blank_lines_are_not_malformed():
    assert aggregate(["", "   ", "\n"])["malformed"] == 0


@pytest.mark.parametrize(
    "line",
    [
        "2026-13-01 10:00:00 ERROR db: month 13",
        "2026-02-29 10:00:00 ERROR db: 2026 is not a leap year",
        "2026-01-01 24:00:00 ERROR db: hour 24",
        "2026-01-01 10:00:00 FATAL db: unknown level",
        "2026-01-01 10:00:00 error db: lowercase level",
        "2026-01-01 10:00 ERROR db: missing seconds",
        "2026-01-01 10:00:00 ERROR db connection refused",
    ],
)
def test_malformed_lines(line):
    r = aggregate([line])
    assert (r["total"], r["malformed"]) == (0, 1)


def test_leap_day_is_valid():
    assert aggregate(["2028-02-29 23:59:59 INFO cron: leap"])["total"] == 1


def test_top_errors_tie_break_is_alphabetical():
    lines = [
        "2026-01-01 10:00:00 ERROR zeta: boom",
        "2026-01-01 10:00:01 ERROR alpha: crash",
        "2026-01-01 10:00:02 CRITICAL alpha: abort",
        "2026-01-01 10:00:03 ERROR zeta: boom",
        "2026-01-01 10:00:04 ERROR alpha: crash",
        "2026-01-01 10:00:05 ERROR mid: oops",
    ]
    assert aggregate(lines, top=10)["top_errors"] == [
        ["alpha", "crash", 2],
        ["zeta", "boom", 2],
        ["alpha", "abort", 1],
        ["mid", "oops", 1],
    ]


def test_top_truncation_and_message_strip():
    lines = [f"2026-01-01 10:00:0{i} ERROR c{i}: msg  " for i in range(5)]
    lines.append("2026-01-01 10:00:09 ERROR c0: msg")
    r = aggregate(lines, top=2)
    assert r["top_errors"] == [["c0", "msg", 2], ["c1", "msg", 1]]


def test_warnings_not_in_top_errors():
    r = aggregate(["2026-01-01 10:00:00 WARNING api: slow"])
    assert r["top_errors"] == [] and r["by_level"] == {"WARNING": 1}


def test_unicode_message_and_crlf():
    r = aggregate(["2026-01-01 10:00:00 ERROR api: समय समाप्त\r\n"])
    assert r["top_errors"] == [["api", "समय समाप्त", 1]]
