# agent-eval-sandbox

A Terminal-Bench-style harness for writing and grading agent coding tasks. Its graders are checked before use: they must fail the untouched setup and known-bad solutions, and pass the reference solution.

[![CI](https://github.com/ansariadeel-hue/agent-eval-sandbox/actions/workflows/ci.yml/badge.svg)](https://github.com/ansariadeel-hue/agent-eval-sandbox/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/ansariadeel-hue/agent-eval-sandbox/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://github.com/ansariadeel-hue/agent-eval-sandbox)

## Why

To write coding tasks for agent evaluation, you write an instruction, a starting environment, a reference solution and a grader. The grader is the part that most often goes wrong. Some common failures:

- The tests pass on the untouched starter code, so an agent that does nothing still gets credit.
- The tests only cover the happy path, so a plausible but wrong fix also passes.
- Some tests are skipped or flaky.

Reviewers catch these by hand, if at all. This harness turns that review into a repeatable **must-fail check**. Each task ships with its reference solution and with the wrong answers the author expects agents to try. `agent-sandbox validate` confirms that the grader tells them apart.

## Features

- **Task folders**: each task has `task.json` (id, instruction, timeout), `setup/`, a reference `solution.py`, grader `tests/` and optional `bad_solutions/`.
- **Isolated runs**:
  - Each run copies the setup into a fresh temp dir and applies the candidate.
  - The grader tests are copied in only after the candidate is applied, so the candidate cannot read or edit them.
  - pytest runs in a subprocess with the task timeout.
- **Two ways to apply a solution**:
  - `"solution_target": "file.py"`: the candidate replaces that file.
  - No target: the candidate is run as a Python script in the work dir, like Terminal-Bench's `solution.sh`.
- **Exact grading**: a run passes only if every collected test passes. Failures, errors, **skips** and "no tests collected" all count as not passed. Counts come from pytest's JUnit XML report.
- **Must-fail validation**:
  - The reference must pass. Use `--repeat N` to catch flaky graders.
  - The no-op (untouched setup) must fail.
  - Every file in `bad_solutions/` must fail.
- **Anti-gaming guards**:
  - A candidate that plants `conftest.py`, `pytest.ini`, `sitecustomize.py`, `pytest.py`, `*.pth` and similar files is marked `tampered`.
  - Tests the candidate writes into the work dir are ignored.
  - pytest runs with its own `-c`/`--rootdir`/`--confcutdir`, and `PYTEST_ADDOPTS` is removed from the environment.
- **Summary tables**, or `--json` output.
- **Three example tasks**: fix a CSV parser bug, write a log aggregator, and write Roman numeral conversion with edge cases. Each has two known-bad solutions.
- Standard library only at runtime. pytest is needed to run the graders.

## Install

```bash
pip install git+https://github.com/ansariadeel-hue/agent-eval-sandbox
pip install pytest   # used to execute the graders
```

## Quickstart

Validate every task's grader:

```bash
agent-sandbox validate tasks/
```

Real output:

```text
task            mode     reference  no-op  bad solutions  time  verdict
--------------  -------  ---------  -----  -------------  ----  -------
fix-csv-parser  replace  pass       fails  2/2 fail       3.0s  VALID
log-aggregator  replace  pass       fails  2/2 fail       2.8s  VALID
roman-numerals  replace  pass       fails  2/2 fail       3.0s  VALID

3/3 tasks valid
```

Grade a candidate solution, for example an agent's fix for the CSV task:

```bash
agent-sandbox run tasks/fix-csv-parser --solution examples/candidates/csv_parser_agent_fix.py
```

```text
task:     fix-csv-parser  (mode: replace, timeout 30s)
solution: csv_parser_agent_fix.py

result  tests  passed  failed  errors  skipped  time
------  -----  ------  ------  ------  -------  -----
PASSED  23     23      0       0       0        0.55s
```

A half-fix that still splits on every comma is rejected:

```bash
agent-sandbox run tasks/fix-csv-parser --solution examples/candidates/csv_parser_naive.py --max-failures 3
```

```text
task:     fix-csv-parser  (mode: replace, timeout 30s)
solution: csv_parser_naive.py

result  tests  passed  failed  errors  skipped  time
------  -----  ------  ------  ------  -------  -----
FAILED  23     12      11      0       0        0.72s

11 test(s) did not pass
  x tests.test_csv_parser::test_matches_csv_module["Smith, John",42,NY]
  x tests.test_csv_parser::test_matches_csv_module["multi, comma, field","x,y"]
  x tests.test_csv_parser::test_matches_csv_module[日本,नमस्ते,"ok, fine"]
  ... and 8 more
```

Other commands and options:

- `agent-sandbox run <task>` with no `--solution` grades the no-op.
- `--reference` grades the reference solution.
- `--keep` keeps the temp dir for debugging.
- `-v` prints the grader output.
- `agent-sandbox list tasks/` shows the available tasks.
- Exit codes: `0` means passed or valid, `1` means failed or invalid, `2` means a usage or data error.

## Task format

```text
tasks/<task-id>/
├── task.json          # see below
├── setup/             # starting files (copied to the work dir)
├── solution.py        # reference solution
├── tests/test_*.py    # grader (pytest); hidden from the candidate
└── bad_solutions/*.py # optional: plausible-but-wrong answers the grader must reject
```

```json
{
  "id": "fix-csv-parser",
  "instruction": "csv_parser.parse_line() splits a CSV record on every delimiter ...",
  "timeout": 30,
  "solution_target": "csv_parser.py",
  "difficulty": "easy",
  "tags": ["bugfix", "parsing"]
}
```

- `id` must match the folder name.
- `timeout` is in seconds, between 0 and 600, and covers both applying the solution and grading.
- `solution_target` is optional. It must be a relative path inside the work dir. If it is missing, solutions are run as scripts.
- Extra keys such as `difficulty` and `tags` are kept as metadata.

Grader tests run with the work dir as the current directory and on `PYTHONPATH`. They can `import` the candidate's module and read setup files through relative paths. The work dir path is also available as `SANDBOX_WORKDIR`.

### Shipped tasks

| task | what the agent must do | known-bad solutions the grader rejects |
|---|---|---|
| `fix-csv-parser` | fix RFC-4180 quoting in `parse_line` without the `csv` module | quote toggling without `""` escapes; delegating to `csv` |
| `log-aggregator` | count levels/hours, validate timestamps, rank top errors | regex-only (accepts `2026-02-30`); `Counter.most_common` tie order |
| `roman-numerals` | `to_roman`/`from_roman` with range, type and canonical-form checks | subtractive-sum parser that accepts `IIII`/`IC`; no range or type checks |

## Limitations

The harness isolates each run in a temp dir and a subprocess. It is **not** a security sandbox: candidates run with your user's permissions and no network or filesystem restrictions. Grade untrusted agent output inside a container or VM.

## Project structure

```text
agent-eval-sandbox/
├── src/agent_sandbox/
│   ├── task.py       # task.json loading, structural checks
│   ├── runner.py     # temp-dir run, solution apply, tamper scan, pytest + JUnit parsing
│   ├── validate.py   # must-fail validation
│   └── cli.py        # `agent-sandbox validate|run|list`
├── tasks/            # three example tasks
├── examples/candidates/  # sample candidate solutions for `run`
├── tests/            # pytest suite (48 tests)
└── .github/workflows/ci.yml
```

Run the tests from the project root with `python -m pytest -q`. `pythonpath` is set in `pyproject.toml`, and `tasks/` is excluded from collection.

## License

MIT © 2026 Ansari Adeel Ahmad. See [LICENSE](LICENSE).
