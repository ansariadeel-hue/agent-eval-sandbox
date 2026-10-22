from pathlib import Path

import pytest

from agent_sandbox.runner import parse_junit, run_task
from agent_sandbox.task import load_task


def test_reference_passes_and_noop_fails(make_task):
    task = load_task(make_task())
    ref = run_task(task, task.reference_solution)
    assert ref.status == "passed" and (ref.passed, ref.total) == (2, 2)
    noop = run_task(task, None)
    assert noop.status == "failed" and noop.passed == 0
    assert noop.label == "no-op"
    assert len(noop.failing_tests) == 2


def test_partial_solution_fails_exact_grading(make_task, tmp_path, write):
    task = load_task(make_task())
    partial = write(tmp_path / "partial.py", "def add(a, b):\n    return abs(a) + abs(b)\n")
    res = run_task(task, partial)
    assert res.status == "failed"
    assert (res.passed, res.failed, res.total) == (1, 1, 2)
    assert res.failing_tests == ["tests.test_grader::test_negative"]


def test_task_folder_is_not_modified(make_task):
    root = make_task()
    before = (root / "setup" / "mathx.py").read_text()
    task = load_task(root)
    run_task(task, task.reference_solution)
    assert (root / "setup" / "mathx.py").read_text() == before


def test_skipped_tests_do_not_count_as_passing(make_task):
    grader = """
        import pytest
        from mathx import add

        def test_ok():
            assert add(1, 1) == 2

        @pytest.mark.skip(reason="author forgot")
        def test_skipped():
            assert False
    """
    task = load_task(make_task(grader=grader))
    res = run_task(task, task.reference_solution)
    assert res.status == "failed" and res.skipped == 1


def test_no_tests_collected_is_an_error(make_task):
    task = load_task(make_task(grader="X = 1\n"))
    res = run_task(task, task.reference_solution)
    assert res.status == "error" and "no tests" in res.detail


def test_timeout(make_task):
    grader = """
        import time

        def test_slow():
            time.sleep(30)
    """
    task = load_task(make_task(grader=grader, timeout=3))
    res = run_task(task, task.reference_solution)
    assert res.status == "timeout"
    assert res.duration < 20


def test_script_mode_solution_edits_files(make_task, tmp_path, write):
    script = write(
        tmp_path / "fix.py",
        """
        from pathlib import Path
        Path("mathx.py").write_text("def add(a, b):\\n    return a + b\\n")
        """,
    )
    task = load_task(make_task(target=None))
    assert run_task(task, script).status == "passed"


def test_script_mode_crash_is_error(make_task, tmp_path, write):
    task = load_task(make_task(target=None))
    crash = write(tmp_path / "crash.py", "raise SystemExit(3)\n")
    res = run_task(task, crash)
    assert res.status == "error" and "code 3" in res.detail


@pytest.mark.parametrize("planted", ["conftest.py", "sitecustomize.py", "pytest.py", "evil.pth"])
def test_tampering_is_detected(make_task, tmp_path, write, planted):
    script = write(
        tmp_path / "game.py",
        f"""
        from pathlib import Path
        Path("{planted}").write_text("import pytest\\n")
        """,
    )
    task = load_task(make_task(target=None))
    res = run_task(task, script)
    assert res.status == "tampered" and planted in res.detail


def test_planted_tests_in_workdir_are_ignored(make_task, tmp_path, write):
    # A candidate that writes its own always-passing tests does not change the grader.
    script = write(
        tmp_path / "plant.py",
        """
        from pathlib import Path
        Path("tests").mkdir(exist_ok=True)
        Path("tests/test_grader.py").write_text("def test_ok():\\n    assert True\\n")
        """,
    )
    task = load_task(make_task(target=None))
    res = run_task(task, script)
    assert res.status == "failed" and res.total == 2


def test_missing_solution_file(make_task, tmp_path):
    task = load_task(make_task())
    res = run_task(task, tmp_path / "nope.py")
    assert res.status == "error" and "not found" in res.detail


def test_keep_workdir(make_task):
    import shutil

    task = load_task(make_task())
    res = run_task(task, task.reference_solution, keep=True)
    kept = Path(res.detail.split("[kept ")[1].rstrip("]"))
    assert (kept / "work" / "mathx.py").read_text() == task.reference_solution.read_text()
    shutil.rmtree(kept)


def test_parse_junit(tmp_path):
    xml = tmp_path / "r.xml"
    xml.write_text(
        """<?xml version="1.0"?>
        <testsuites><testsuite name="pytest" tests="4">
          <testcase classname="tests.t" name="a"/>
          <testcase classname="tests.t" name="b"><failure message="x"/></testcase>
          <testcase classname="tests.t" name="c"><error message="y"/></testcase>
          <testcase classname="tests.t" name="d"><skipped message="z"/></testcase>
        </testsuite></testsuites>""",
        encoding="utf-8",
    )
    total, failed, errors, skipped, failing = parse_junit(xml)
    assert (total, failed, errors, skipped) == (4, 1, 1, 1)
    assert failing == ["tests.t::b", "tests.t::c", "tests.t::d (skipped)"]
