"""Must-fail validation of a task's grader.

A grader is trustworthy only if it

* PASSES the reference solution (every time, if ``repeat`` > 1 -> no flakiness),
* FAILS the untouched setup (no-op solution), and
* FAILS every known-bad solution in ``bad_solutions/``.

Otherwise an agent could score by doing nothing, or by a plausible-but-wrong
fix the task author already anticipated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .runner import RunResult, run_task
from .task import Task, structure_problems


@dataclass
class Expectation:
    label: str
    expect_pass: bool
    result: RunResult

    @property
    def ok(self) -> bool:
        return self.result.ok == self.expect_pass

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "expect": "pass" if self.expect_pass else "fail",
            "ok": self.ok,
            "result": self.result.to_dict(),
        }


@dataclass
class ValidationReport:
    task: Task
    problems: list[str] = field(default_factory=list)
    checks: list[Expectation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.problems and bool(self.checks) and all(c.ok for c in self.checks)

    def _group(self, prefix: str) -> list[Expectation]:
        return [c for c in self.checks if c.label.startswith(prefix)]

    def reference_cell(self) -> str:
        refs = self._group("reference")
        if not refs:
            return "-"
        return f"{'pass' if all(c.ok for c in refs) else 'FAIL'}" + (f" x{len(refs)}" if len(refs) > 1 else "")

    def noop_cell(self) -> str:
        noop = self._group("no-op")
        if not noop:
            return "-"
        return "fails" if noop[0].ok else "PASSES!"

    def bad_cell(self) -> str:
        bad = self._group("bad:")
        if not bad:
            return "none"
        return f"{sum(c.ok for c in bad)}/{len(bad)} fail"

    def failures(self) -> list[str]:
        msgs = list(self.problems)
        for c in self.checks:
            if not c.ok:
                want = "pass" if c.expect_pass else "fail"
                msgs.append(f"{c.label}: expected grader to {want}, got {c.result.summary()}")
        return msgs

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task.id,
            "valid": self.valid,
            "problems": self.problems,
            "warnings": self.warnings,
            "checks": [c.to_dict() for c in self.checks],
        }


def validate_task(task: Task, repeat: int = 1) -> ValidationReport:
    if repeat < 1:
        raise ValueError("repeat must be >= 1")
    report = ValidationReport(task, problems=structure_problems(task))
    if report.problems:
        return report
    for i in range(repeat):
        label = "reference" if repeat == 1 else f"reference#{i + 1}"
        report.checks.append(Expectation(label, True, run_task(task, task.reference_solution, label)))
    report.checks.append(Expectation("no-op", False, run_task(task, None, "no-op")))
    for bad in task.bad_solutions:
        label = f"bad:{bad.name}"
        report.checks.append(Expectation(label, False, run_task(task, bad, label)))
    if not task.bad_solutions:
        report.warnings.append("no bad_solutions/ provided; only the no-op must-fail check ran")
    for c in report.checks:
        if not c.expect_pass and c.result.status in ("timeout", "error"):
            report.warnings.append(
                f"{c.label} failed via {c.result.status} ({c.result.detail}), not via a failing assertion"
            )
    return report
