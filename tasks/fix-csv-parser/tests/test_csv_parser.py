"""Grader for fix-csv-parser. Expected values come from Python's csv module."""

import csv
import re
from pathlib import Path

import pytest

import csv_parser

LINES = [
    "a,b,c",
    '"Smith, John",42,NY',
    '"say ""hi""",x',
    '"",""',
    "a,,b,",
    " a , b ",
    'a"b,c',
    '"multi, comma, field","x,y"',
    '"""quoted at start",z',
    "single",
    "日本,नमस्ते,\"ok, fine\"",
]


def reference(line, delimiter=","):
    return next(csv.reader([line], delimiter=delimiter))


@pytest.mark.parametrize("line", LINES)
def test_matches_csv_module(line):
    assert csv_parser.parse_line(line) == reference(line)


def test_quoted_delimiter():
    assert csv_parser.parse_line('"Smith, John",42') == ["Smith, John", "42"]


def test_escaped_quotes():
    assert csv_parser.parse_line('"say ""hi"""') == ['say "hi"']


def test_trailing_newlines_ignored():
    assert csv_parser.parse_line("a,b\r\n") == ["a", "b"]
    assert csv_parser.parse_line("a,b\n") == ["a", "b"]


def test_empty_line_is_one_empty_field():
    assert csv_parser.parse_line("") == [""]


@pytest.mark.parametrize("bad", ['"abc', 'a,"b,c', '"x""'])
def test_unterminated_quote_raises(bad):
    with pytest.raises(ValueError):
        csv_parser.parse_line(bad)


@pytest.mark.parametrize("delimiter", [";", "\t", "|"])
def test_custom_delimiter(delimiter):
    line = f'a{delimiter}"b{delimiter}c"{delimiter}d'
    assert csv_parser.parse_line(line, delimiter=delimiter) == reference(line, delimiter)


def test_parse_multiple_lines_skips_blank():
    text = 'id,name\n1,"Doe, Jane"\n\n2,"O""Brien"\n'
    assert csv_parser.parse(text) == [["id", "name"], ["1", "Doe, Jane"], ["2", 'O"Brien']]


def test_does_not_use_csv_module():
    src = Path(csv_parser.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import\s+csv\b|from\s+csv\s+import)", src, re.M)
