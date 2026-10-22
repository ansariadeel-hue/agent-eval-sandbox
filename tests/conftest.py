import json
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TASKS = REPO / "tasks"
EXAMPLES = REPO / "examples"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    return path


GOOD_ADD = "def add(a, b):\n    return a + b\n"
STUB_ADD = "def add(a, b):\n    raise NotImplementedError\n"
GRADER_ADD = """
    from mathx import add

    def test_small():
        assert add(2, 3) == 5

    def test_negative():
        assert add(-2, -3) == -5
"""


@pytest.fixture
def make_task(tmp_path):
    """Build a tiny task folder: setup/mathx.py stub, solution.py, tests/."""

    def factory(
        task_id="add-task",
        *,
        timeout=60,
        target="mathx.py",
        setup=STUB_ADD,
        solution=GOOD_ADD,
        grader=GRADER_ADD,
        bad=None,
        extra=None,
    ):
        root = tmp_path / task_id
        cfg = {"id": task_id, "instruction": "Implement add(a, b) in mathx.py.", "timeout": timeout}
        if target:
            cfg["solution_target"] = target
        _write(root / "task.json", json.dumps(cfg))
        if setup is not None:
            _write(root / "setup" / "mathx.py", setup)
        if solution is not None:
            _write(root / "solution.py", solution)
        if grader is not None:
            _write(root / "tests" / "test_grader.py", grader)
        for name, text in (bad or {}).items():
            _write(root / "bad_solutions" / name, text)
        for rel, text in (extra or {}).items():
            _write(root / rel, text)
        return root

    return factory


@pytest.fixture
def write():
    return _write
