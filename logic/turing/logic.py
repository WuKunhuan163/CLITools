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

class TuringError(Exception):
    """Custom exception for reporting detailed errors in Turing stages."""
    def __init__(self, brief: str, full: Optional[str] = None):
        self.brief = brief
        self.full = full or brief
        super().__init__(brief)

class TuringStage:
    """Represents a single stage in a command execution pipeline."""
    def __init__(self, name: str, action: Callable[..., bool], 
                 active_status: str = "Running", 
                 success_status: str = "Successfully", 
                 fail_status: str = "Failed",
                 success_color: str = "GREEN",
                 fail_color: str = "RED",
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
        self.fail_color = fail_color
        self.is_sticky = is_sticky
        self.active_name = active_name
        self.success_name = success_name
        self.fail_name = fail_name
        self.bold_part = bold_part
        
        # Support for failure information and captured output
        self.error_brief: Optional[str] = None 
        self.error_full: Optional[str] = None  
        self.captured_output: Optional[str] = None # NEW: Captured stdout/stderr from commands

    def report_error(self, brief: str, full: Optional[str] = None):
        """Allows the action to report detailed error information."""
        self.error_brief = brief
        self.error_full = full or brief

    def set_captured_output(self, output: str):
        """Sets captured output from commands to be included in logs."""
        self.captured_output = output

