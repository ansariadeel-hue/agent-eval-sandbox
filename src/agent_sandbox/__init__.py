"""agent_sandbox: author and grade agent coding tasks with exact, must-fail-checked graders."""

from .task import Task, TaskError, discover_tasks, load_task
from .runner import RunResult, run_task
from .validate import ValidationReport, validate_task

__version__ = "0.1.0"

__all__ = [
    "Task",
    "TaskError",
    "discover_tasks",
    "load_task",
    "RunResult",
    "run_task",
    "ValidationReport",
    "validate_task",
]
