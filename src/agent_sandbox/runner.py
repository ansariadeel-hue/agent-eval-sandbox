"""Run one candidate solution against a task's grader in an isolated temp dir.

Steps:

1. copy ``setup/`` into ``<tmp>/work``;
2. apply the candidate (replace ``solution_target`` or execute the script);
3. scan the work dir for files that could hijack pytest or the interpreter;
4. copy ``tests/`` into ``<tmp>/grader/tests`` (after the solution ran, so the
   candidate never sees or edits the grader);
5. run pytest in a subprocess with a timeout and a JUnit XML report;
6. grade exactly: PASS only if every collected test passed (no failures,
   errors or skips, and at least one test).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .task import Task

PASSED = "passed"
FAILED = "failed"
TIMEOUT = "timeout"
ERROR = "error"
TAMPERED = "tampered"

# Files that, if planted in the work dir, could change how the grader runs.
FORBIDDEN_NAMES = {
    "conftest.py",
    "pytest.ini",
    "pytest.py",
    "_pytest",
    "py.py",
    "sitecustomize.py",
    "usercustomize.py",
}


@dataclass
class RunResult:
    task_id: str
    label: str
    status: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    failing_tests: list[str] = field(default_factory=list)
    detail: str = ""
    output: str = ""

    @property
    def ok(self) -> bool:
        return self.status == PASSED

    def summary(self) -> str:
        if self.status in (TIMEOUT, TAMPERED) or (self.status == ERROR and not self.total):
            return f"{self.status.upper()}: {self.detail}"
        return f"{self.status.upper()} ({self.passed}/{self.total} tests passed)"

    def to_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items() if k != "output"}
        d["duration"] = round(self.duration, 3)
        return d


def _tail(text: str, n: int = 40) -> str:
    return "\n".join(text.splitlines()[-n:])


def _scan_tampering(work: Path, allowed: set[str]) -> list[str]:
    bad = []
    for p in work.rglob("*"):
        rel = p.relative_to(work).as_posix()
        if rel in allowed:
            continue
        if p.name in FORBIDDEN_NAMES or p.suffix == ".pth":
            bad.append(rel)
    return sorted(bad)


def _clean_env(work: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONSTARTUP", "PYTHONINSPECT"):
        env.pop(key, None)
    env["PYTHONPATH"] = str(work) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["SANDBOX_WORKDIR"] = str(work)
    return env


def parse_junit(path: Path) -> tuple[int, int, int, int, list[str]]:
    """Return (total, failed, errors, skipped, failing test ids) from a JUnit XML file."""
    root = ET.parse(path).getroot()
    total = failed = errors = skipped = 0
    failing: list[str] = []
    for case in root.iter("testcase"):
        total += 1
        name = f"{case.get('classname', '')}::{case.get('name', '')}".strip(":")
        if case.find("failure") is not None:
            failed += 1
            failing.append(name)
        elif case.find("error") is not None:
            errors += 1
            failing.append(name)
        elif case.find("skipped") is not None:
            skipped += 1
            failing.append(name + " (skipped)")
    return total, failed, errors, skipped, failing


def _apply_solution(task: Task, solution: Path | None, work: Path, deadline: float) -> str | None:
    """Apply the candidate. Returns an error message or None."""
    if solution is None:
        return None
    solution = solution.resolve()
    if not solution.is_file():
        return f"solution file not found: {solution}"
    if task.solution_target:
        dest = work / task.solution_target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(solution, dest)
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(solution)],
            cwd=work,
            env=_clean_env(work),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(0.1, deadline - time.monotonic()),
        )
    except subprocess.TimeoutExpired:
        return "timeout: solution script exceeded the task timeout"
    if proc.returncode != 0:
        return f"solution script exited with code {proc.returncode}: {_tail(proc.stderr, 5)}"
    return None


def run_task(
    task: Task,
    solution: str | Path | None,
    label: str | None = None,
    keep: bool = False,
    timeout: float | None = None,
) -> RunResult:
    """Grade ``solution`` (None = no-op, i.e. untouched setup) against ``task``."""
    sol = None if solution is None else Path(solution)
    label = label or ("no-op" if sol is None else sol.name)
    limit = timeout if timeout is not None else task.timeout
    tmp = Path(tempfile.mkdtemp(prefix=f"agent-sandbox-{task.id}-"))
    start = time.monotonic()
    deadline = start + limit
    result = RunResult(task.id, label, ERROR)
    try:
        work = tmp / "work"
        if task.setup_dir.is_dir():
            shutil.copytree(task.setup_dir, work)
        else:
            work.mkdir()
        allowed = {p.relative_to(work).as_posix() for p in work.rglob("*")}

        err = _apply_solution(task, sol, work, deadline)
        if err:
            result.status = TIMEOUT if err.startswith("timeout") else ERROR
            result.detail = err
            return result

        tampered = _scan_tampering(work, allowed)
        if tampered:
            result.status = TAMPERED
            result.detail = "forbidden files in work dir: " + ", ".join(tampered)
            return result

        grader = tmp / "grader"
        shutil.copytree(task.tests_dir, grader / "tests")
        ini = grader / "pytest.ini"
        ini.write_text("[pytest]\n", encoding="utf-8")
        report = grader / "report.xml"
        cmd = [
            sys.executable, "-m", "pytest", "-q",
            "-p", "no:cacheprovider",
            "-c", str(ini),
            "--rootdir", str(grader),
            "--confcutdir", str(grader),
            f"--junitxml={report}",
            str(grader / "tests"),
        ]
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result.status, result.detail = TIMEOUT, f"exceeded {limit:g}s before grading"
            return result
        try:
            proc = subprocess.run(
                cmd,
                cwd=work,
                env=_clean_env(work),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=remaining,
            )
        except subprocess.TimeoutExpired as exc:
            result.status = TIMEOUT
            result.detail = f"grader exceeded {limit:g}s"
            out = exc.stdout or ""
            result.output = out if isinstance(out, str) else out.decode("utf-8", "replace")
            return result

        result.output = proc.stdout + proc.stderr
        if not report.is_file():
            result.status = ERROR
            result.detail = f"pytest exited with code {proc.returncode} and wrote no report"
            return result
        total, failed, errors, skipped, failing = parse_junit(report)
        result.total, result.failed, result.errors, result.skipped = total, failed, errors, skipped
        result.passed = total - failed - errors - skipped
        result.failing_tests = failing
        if total == 0:
            result.status, result.detail = ERROR, "no tests were collected"
        elif proc.returncode == 0 and result.passed == total:
            result.status = PASSED
        else:
            result.status = FAILED
            result.detail = f"{len(failing)} test(s) did not pass"
        return result
    finally:
        result.duration = time.monotonic() - start
        if keep:
            result.detail = (result.detail + f" [kept {tmp}]").strip()
        else:
            shutil.rmtree(tmp, ignore_errors=True)
