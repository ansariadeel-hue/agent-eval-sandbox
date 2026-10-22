"""Task folder model.

A task is a directory::

    <task-id>/
        task.json          {"id", "instruction", "timeout", "solution_target"?, ...}
        setup/             files the agent starts with (copied into the work dir)
        solution.py        reference solution
        tests/             grader tests (pytest), hidden from the agent
        bad_solutions/     optional known-bad solutions the grader must reject

``solution_target`` selects how a solution is applied:

* set (e.g. ``"csv_parser.py"``): the solution file *replaces* that path in the work dir;
* absent: the solution is *executed* as a Python script with the work dir as cwd
  (like Terminal-Bench's ``solution.sh``), and may edit any files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

MAX_TIMEOUT = 600


class TaskError(ValueError):
    """Raised when a task folder is malformed."""


@dataclass
class Task:
    id: str
    root: Path
    instruction: str
    timeout: float
    solution_target: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def setup_dir(self) -> Path:
        return self.root / "setup"

    @property
    def tests_dir(self) -> Path:
        return self.root / "tests"

    @property
    def reference_solution(self) -> Path:
        return self.root / "solution.py"

    @property
    def bad_solutions(self) -> list[Path]:
        d = self.root / "bad_solutions"
        return sorted(p for p in d.glob("*.py")) if d.is_dir() else []

    @property
    def mode(self) -> str:
        return "replace" if self.solution_target else "script"

    def test_files(self) -> list[Path]:
        return sorted(self.tests_dir.glob("test_*.py")) if self.tests_dir.is_dir() else []


def _check_target(target: Any) -> str:
    if not isinstance(target, str) or not target.strip():
        raise TaskError("'solution_target' must be a non-empty string")
    p = PurePosixPath(target.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or ":" in target:
        raise TaskError(f"'solution_target' must be a relative path inside the work dir: {target!r}")
    return str(p)


def load_task(path: str | Path) -> Task:
    root = Path(path).resolve()
    cfg = root / "task.json"
    if not cfg.is_file():
        raise TaskError(f"{root}: missing task.json")
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskError(f"{cfg}: invalid JSON ({exc.msg})") from None
    if not isinstance(data, dict):
        raise TaskError(f"{cfg}: expected a JSON object")
    for key in ("id", "instruction", "timeout"):
        if key not in data:
            raise TaskError(f"{cfg}: missing required field '{key}'")
    tid = data["id"]
    if not isinstance(tid, str) or not tid.strip():
        raise TaskError(f"{cfg}: 'id' must be a non-empty string")
    instruction = data["instruction"]
    if not isinstance(instruction, str) or not instruction.strip():
        raise TaskError(f"{cfg}: 'instruction' must be a non-empty string")
    timeout = data["timeout"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= MAX_TIMEOUT:
        raise TaskError(f"{cfg}: 'timeout' must be a number in (0, {MAX_TIMEOUT}] seconds")
    target = data.get("solution_target")
    if target is not None:
        target = _check_target(target)
    meta = {k: v for k, v in data.items() if k not in {"id", "instruction", "timeout", "solution_target"}}
    return Task(tid, root, instruction.strip(), float(timeout), target, meta)


def discover_tasks(path: str | Path) -> list[Path]:
    """Return task directories: ``path`` itself if it has task.json, else its children that do."""
    p = Path(path)
    if (p / "task.json").is_file():
        return [p]
    if not p.is_dir():
        raise TaskError(f"{p}: not a directory")
    return sorted(c for c in p.iterdir() if (c / "task.json").is_file())


def structure_problems(task: Task) -> list[str]:
    """Static checks that do not need to run anything."""
    problems: list[str] = []
    if task.id != task.root.name:
        problems.append(f"id {task.id!r} does not match folder name {task.root.name!r}")
    if not task.reference_solution.is_file():
        problems.append("missing reference solution.py")
    if not task.test_files():
        problems.append("tests/ has no test_*.py files")
    if task.setup_dir.exists() and not task.setup_dir.is_dir():
        problems.append("setup must be a directory")
    for p in task.setup_dir.rglob("*") if task.setup_dir.is_dir() else []:
        if p.name.startswith("test_") and p.suffix == ".py":
            problems.append(f"setup/ contains a test file ({p.name}); graders belong in tests/")
    return problems
