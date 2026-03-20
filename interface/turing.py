"""Turing Machine interface for tools.

Provides all commonly-used Turing Machine classes and helpers.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from logic._.utils.turing.models.progress import ProgressTuringMachine
from logic._.utils.turing.logic import TuringStage, TuringTask, StepResult, WorkerState
from logic._.utils.turing.worker import TuringWorker
from logic._.utils.turing.models.worker import ParallelWorkerPool
from logic._.utils.turing.display.manager import MultiLineManager, _get_configured_width, truncate_to_width
from logic._.utils.turing.terminal.keyboard import get_global_suppressor
from logic._.utils.turing.select import select_menu, select_horizontal, read_masked, erase_lines
from logic._.utils.turing.multiline_input import multiline_input

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
