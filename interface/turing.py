"""Turing Machine interface for tools.

Provides all commonly-used Turing Machine classes and helpers.
"""
from logic.utils.turing.models.progress import ProgressTuringMachine
from logic.utils.turing.logic import TuringStage, TuringTask, StepResult, WorkerState
from logic.utils.turing.worker import TuringWorker
from logic.utils.turing.models.worker import ParallelWorkerPool
from logic.utils.turing.display.manager import MultiLineManager, _get_configured_width, truncate_to_width
from logic.utils.turing.terminal.keyboard import get_global_suppressor
from logic.utils.turing.select import select_menu, select_horizontal, read_masked, erase_lines
from logic.utils.turing.multiline_input import multiline_input

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
    "select_menu",
    "select_horizontal",
    "read_masked",
    "erase_lines",
    "multiline_input",
]
