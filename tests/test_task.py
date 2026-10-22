import json

import pytest

from agent_sandbox.task import TaskError, discover_tasks, load_task, structure_problems


def test_load_task_fields(make_task):
    t = load_task(make_task(timeout=12))
    assert t.id == "add-task"
    assert t.timeout == 12.0
    assert t.solution_target == "mathx.py"
    assert t.mode == "replace"
    assert [p.name for p in t.test_files()] == ["test_grader.py"]
    assert structure_problems(t) == []


def test_script_mode_when_no_target(make_task):
    assert load_task(make_task(target=None)).mode == "script"


@pytest.mark.parametrize("field", ["id", "instruction", "timeout"])
def test_missing_required_field(make_task, field):
    root = make_task()
    cfg = json.loads((root / "task.json").read_text())
    del cfg[field]
    (root / "task.json").write_text(json.dumps(cfg))
    with pytest.raises(TaskError, match=field):
        load_task(root)


@pytest.mark.parametrize("timeout", [0, -5, True, "30", 10_000])
def test_invalid_timeout(make_task, timeout):
    root = make_task()
    cfg = json.loads((root / "task.json").read_text())
    cfg["timeout"] = timeout
    (root / "task.json").write_text(json.dumps(cfg))
    with pytest.raises(TaskError, match="timeout"):
        load_task(root)


@pytest.mark.parametrize("target", ["../escape.py", "/abs/path.py", "C:/x.py", ""])
def test_solution_target_must_stay_inside_workdir(make_task, target):
    root = make_task()
    cfg = json.loads((root / "task.json").read_text())
    cfg["solution_target"] = target
    (root / "task.json").write_text(json.dumps(cfg))
    with pytest.raises(TaskError):
        load_task(root)


def test_missing_task_json(tmp_path):
    with pytest.raises(TaskError, match="task.json"):
        load_task(tmp_path)


def test_discover_tasks(make_task, tmp_path):
    a = make_task("a-task")
    make_task("b-task")
    (tmp_path / "not-a-task").mkdir()
    assert [p.name for p in discover_tasks(tmp_path)] == ["a-task", "b-task"]
    assert discover_tasks(a) == [a]


def test_structure_problems(make_task, write):
    root = make_task("folder-name", solution=None, grader=None)
    cfg = json.loads((root / "task.json").read_text())
    cfg["id"] = "other-id"
    (root / "task.json").write_text(json.dumps(cfg))
    write(root / "setup" / "test_leak.py", "def test_x(): pass\n")
    problems = structure_problems(load_task(root))
    assert any("does not match folder" in p for p in problems)
    assert any("solution.py" in p for p in problems)
    assert any("test_*.py" in p for p in problems)
    assert any("setup/ contains a test file" in p for p in problems)
