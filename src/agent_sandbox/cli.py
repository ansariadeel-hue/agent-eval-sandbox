"""Command-line interface: ``agent-sandbox validate|run|list``."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path
from typing import Any

from . import __version__
from .runner import run_task
from .task import TaskError, discover_tasks, load_task
from .validate import validate_task


def format_table(headers: list[str], rows: list[list[Any]]) -> str:
    cells = [[str(h) for h in headers]] + [[str(c) for c in r] for r in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(headers))]
    lines = ["  ".join(c.ljust(widths[i]) for i, c in enumerate(r)).rstrip() for r in cells]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def _cmd_validate(args: argparse.Namespace) -> int:
    dirs = discover_tasks(args.path)
    if not dirs:
        raise TaskError(f"no tasks (folders with task.json) under {args.path}")
    reports = []
    for d in dirs:
        try:
            task = load_task(d)
        except TaskError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if not args.json:
            print(f"validating {task.id} ...", file=sys.stderr, flush=True)
        reports.append(validate_task(task, repeat=args.repeat))

    if args.json:
        print(json.dumps({"valid": all(r.valid for r in reports), "tasks": [r.to_dict() for r in reports]}, indent=2))
        return 0 if all(r.valid for r in reports) else 1

    rows = []
    for r in reports:
        secs = sum(c.result.duration for c in r.checks)
        rows.append(
            [r.task.id, r.task.mode, r.reference_cell(), r.noop_cell(), r.bad_cell(),
             f"{secs:.1f}s", "VALID" if r.valid else "INVALID"]
        )
    print(format_table(["task", "mode", "reference", "no-op", "bad solutions", "time", "verdict"], rows))
    for r in reports:
        for msg in r.failures():
            print(f"  [{r.task.id}] {msg}")
        for msg in r.warnings:
            print(f"  [{r.task.id}] warning: {msg}")
    n_ok = sum(r.valid for r in reports)
    print(f"\n{n_ok}/{len(reports)} tasks valid")
    return 0 if n_ok == len(reports) else 1


def _cmd_run(args: argparse.Namespace) -> int:
    task = load_task(args.task)
    if args.reference and args.solution:
        raise TaskError("use either --solution or --reference, not both")
    solution = task.reference_solution if args.reference else args.solution
    res = run_task(task, solution, keep=args.keep, timeout=args.timeout)
    if args.json:
        out = res.to_dict()
        if args.verbose:
            out["output"] = res.output
        print(json.dumps(out, indent=2))
        return 0 if res.ok else 1
    print(f"task:     {task.id}  (mode: {task.mode}, timeout {task.timeout:g}s)")
    print(f"solution: {res.label}\n")
    rows = [[res.status.upper(), res.total, res.passed, res.failed, res.errors, res.skipped, f"{res.duration:.2f}s"]]
    print(format_table(["result", "tests", "passed", "failed", "errors", "skipped", "time"], rows))
    if res.detail:
        print(f"\n{res.detail}")
    for name in res.failing_tests[: args.max_failures]:
        print(f"  x {name}")
    if len(res.failing_tests) > args.max_failures:
        print(f"  ... and {len(res.failing_tests) - args.max_failures} more")
    if args.verbose and res.output:
        print("\n--- grader output ---\n" + res.output.rstrip())
    return 0 if res.ok else 1


def _cmd_list(args: argparse.Namespace) -> int:
    rows = []
    for d in discover_tasks(args.path):
        t = load_task(d)
        first = textwrap.shorten(t.instruction, width=60, placeholder="...")
        rows.append([t.id, t.mode, f"{t.timeout:g}s", len(t.test_files()), len(t.bad_solutions), first])
    print(format_table(["task", "mode", "timeout", "test files", "bad", "instruction"], rows))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent-sandbox", description="Author and grade agent coding tasks.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="must-fail check: reference passes, no-op and bad solutions fail")
    v.add_argument("path", help="a task folder or a folder of tasks")
    v.add_argument("--repeat", type=int, default=1, help="run the reference N times to detect flaky graders")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=_cmd_validate)

    r = sub.add_parser("run", help="grade one candidate solution against a task")
    r.add_argument("task", help="task folder")
    r.add_argument("--solution", help="candidate solution file (omit for a no-op run)")
    r.add_argument("--reference", action="store_true", help="grade the task's reference solution")
    r.add_argument("--timeout", type=float, help="override the task timeout (seconds)")
    r.add_argument("--keep", action="store_true", help="keep the temp work dir for inspection")
    r.add_argument("--max-failures", type=int, default=10)
    r.add_argument("-v", "--verbose", action="store_true", help="show grader output")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=_cmd_run)

    ls = sub.add_parser("list", help="list tasks")
    ls.add_argument("path")
    ls.set_defaults(func=_cmd_list)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    try:
        return args.func(args)
    except (TaskError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
