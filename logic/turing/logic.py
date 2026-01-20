from typing import List, Callable, Any, Dict, Optional, Union

class WorkerState:
    CONTINUE = "CONTINUE"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    EXIT = "EXIT"

class StepResult:
    def __init__(self, display_text: str, state: str = WorkerState.CONTINUE, is_final: bool = False):
        self.display_text = display_text
        self.state = state
        self.is_final = is_final

class TuringTask:
    def __init__(self, name: str, steps: List[Callable[..., Any]]):
        self.name = name
        self.steps = steps

class TuringStage:
    """Represents a single stage in a command execution pipeline."""
    def __init__(self, name: str, action: Callable[[], bool], 
                 active_status: str = "Running", 
                 success_status: str = "Successfully", 
                 fail_status: str = "Failed",
                 success_color: str = "GREEN",
                 is_sticky: bool = False,
                 active_name: Optional[str] = None,
                 success_name: Optional[str] = None,
                 fail_name: Optional[str] = None,
                 bold_part: Optional[str] = None):
        self.name = name
        self.action = action
        self.active_status = active_status
        self.success_status = success_status
        self.fail_status = fail_status
        self.success_color = success_color
        self.is_sticky = is_sticky
        self.active_name = active_name
        self.success_name = success_name
        self.fail_name = fail_name
        self.bold_part = bold_part

