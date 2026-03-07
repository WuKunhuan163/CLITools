"""Turing Machine interface for tools.

Provides all commonly-used Turing Machine classes and helpers.
"""
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage, TuringTask, StepResult, WorkerState
from logic.turing.worker import TuringWorker
from logic.turing.models.worker import ParallelWorkerPool
from logic.turing.display.manager import MultiLineManager, _get_configured_width, truncate_to_width
from logic.turing.terminal.keyboard import get_global_suppressor

__all__ = [
    "ProgressTuringMachine",
    "TuringStage",
    "TuringTask",
    "StepResult",
    "WorkerState",
    "TuringWorker",
    "ParallelWorkerPool",
    "MultiLineManager",
    "_get_configured_width",
    "truncate_to_width",
    "get_global_suppressor",
]
