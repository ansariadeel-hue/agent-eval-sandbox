import json

import pytest

from agent_sandbox.cli import main
from agent_sandbox.task import discover_tasks, load_task
from agent_sandbox.validate import validate_task

from conftest import EXAMPLES, GOOD_ADD, STUB_ADD, TASKS


def test_valid_task_with_bad_solutions(make_task):
    root = make_task(bad={"abs_add.py": "def add(a, b):\n    return abs(a) + abs(b)\n"})
    report = validate_task(load_task(root))
    assert report.valid
    assert [c.label for c in report.checks] == ["reference", "no-op", "bad:abs_add.py"]
    assert (report.reference_cell(), report.noop_cell(), report.bad_cell()) == ("pass", "fails", "1/1 fail")
    assert report.warnings == []


def test_trivially_gameable_grader_is_invalid(make_task):
    # Grader that never imports the solution: the untouched setup passes.
    root = make_task(grader="def test_nothing():\n    assert True\n")
    report = validate_task(load_task(root))
    assert not report.valid
    assert report.noop_cell() == "PASSES!"
    assert any("no-op: expected grader to fail" in m for m in report.failures())
    assert any("bad_solutions" in w for w in report.warnings)


def test_grader_that_accepts_known_bad_solution_is_invalid(make_task):
    weak = "from mathx import add\n\ndef test_small():\n    assert add(2, 3) == 5\n"
    root = make_task(grader=weak, bad={"abs_add.py": "def add(a, b):\n    return abs(a) + abs(b)\n"})
    report = validate_task(load_task(root))
    assert not report.valid
    assert report.bad_cell() == "0/1 fail"


def test_broken_reference_is_invalid(make_task):
    report = validate_task(load_task(make_task(solution=STUB_ADD)))
    assert not report.valid and report.reference_cell() == "FAIL"


def test_structure_problems_skip_runs(make_task):
    report = validate_task(load_task(make_task(grader=None)))
    assert not report.valid and report.checks == []


def test_repeat_runs_reference_multiple_times(make_task):
    report = validate_task(load_task(make_task(setup=STUB_ADD, solution=GOOD_ADD)), repeat=2)
    assert [c.label for c in report.checks][:2] == ["reference#1", "reference#2"]
    assert report.reference_cell() == "pass x2"


@pytest.mark.parametrize("task_dir", discover_tasks(TASKS), ids=lambda p: p.name)
def test_shipped_example_tasks_are_valid(task_dir):
    task = load_task(task_dir)
    assert len(task.bad_solutions) >= 2
    report = validate_task(task)
    assert report.valid, report.failures()


def test_cli_validate_table(make_task, tmp_path, capsys):
    make_task("t1")
    assert main(["validate", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "t1" in out and "VALID" in out and "1/1 tasks valid" in out


def test_cli_validate_invalid_exit_code(make_task, capsys):
    root = make_task(grader="def test_nothing():\n    assert True\n")
    assert main(["validate", str(root), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["valid"] is False and data["tasks"][0]["task"] == "add-task"


def test_cli_run_example_candidates(capsys):
    task = str(TASKS / "fix-csv-parser")
    assert main(["run", task, "--solution", str(EXAMPLES / "candidates" / "csv_parser_agent_fix.py")]) == 0
    assert "PASSED" in capsys.readouterr().out
    assert main(["run", task, "--solution", str(EXAMPLES / "candidates" / "csv_parser_naive.py"), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "failed" and data["failed"] > 0


def test_cli_run_reference_and_noop(make_task, capsys):
    root = str(make_task())
    assert main(["run", root, "--reference"]) == 0
    assert main(["run", root]) == 1
    assert "no-op" in capsys.readouterr().out


def test_cli_list(capsys):
    assert main(["list", str(TASKS)]) == 0
    out = capsys.readouterr().out
    assert "fix-csv-parser" in out and "roman-numerals" in out


def test_cli_bad_path(tmp_path, capsys):
    assert main(["validate", str(tmp_path / "missing")]) == 2
    assert "error:" in capsys.readouterr().err
