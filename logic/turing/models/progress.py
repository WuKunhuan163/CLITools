import sys
import os
import re
import inspect
from typing import List, Optional
from pathlib import Path
from logic.turing.logic import TuringStage
from logic._.config import get_color
from logic.turing.terminal.keyboard import get_global_suppressor
from logic._.lang.utils import get_translation
from logic.utils import get_logic_dir, find_project_root

# Global manager for synchronization across components
_GLOBAL_TURING_MANAGER = None

def get_global_turing_manager():
    return _GLOBAL_TURING_MANAGER

class ProgressTuringMachine:
    """Executes a sequence of TuringStages with erasable progress display."""
    def __init__(self, stages: List[TuringStage] = None, project_root: Optional[str] = None, 
                 tool_name: Optional[str] = None, log_dir: Optional[str] = None,
                 no_warning: bool = False, manager: Optional['MultiLineManager'] = None,
                 session_logger=None):
        from logic.turing.display.manager import MultiLineManager
        global _GLOBAL_TURING_MANAGER
        self.stages = stages or []
        self.no_warning = no_warning
        self.manager = manager or MultiLineManager()
        _GLOBAL_TURING_MANAGER = self.manager
        self.project_root = Path(project_root) if project_root else None
        self.tool_name = tool_name
        self.log_dir = Path(log_dir) if log_dir else None
        self.session_logger = session_logger

    def add_stage(self, stage: TuringStage):
        self.stages.append(stage)

    def warning(self, text: str) -> None:
        """Emit a dimmed warning line via the display manager."""
        from logic.turing.status import fmt_warning
        self.manager.update(
            f"_warn_{id(text)}",
            fmt_warning(text, indent=0),
            is_final=True, truncate=False)

    def info(self, text: str) -> None:
        """Emit a dimmed informational line via the display manager."""
        from logic.turing.status import fmt_info
        self.manager.update(
            f"_info_{id(text)}",
            fmt_info(text, indent=0),
            is_final=True, truncate=False)

    def _log_error(self, stage: TuringStage, exception: Optional[Exception] = None):
        """Saves full error information to the session log or a standalone file."""
        from logic.turing.utils import log_turing_error
        return log_turing_error(stage, self.project_root, self.tool_name, exception,
                                log_dir=self.log_dir, session_logger=self.session_logger)

    @staticmethod
    def _format_msg(status: str, name: str, color: str, bold_part: str = None,
                    suffix: str = "") -> str:
        """Build a formatted stage message.

        *status* + *name* form the full text.  *bold_part* selects the
        prefix to render in *color* (BOLD for active, GREEN/RED for done/fail).
        The rest stays in default style.
        """
        RESET = get_color("RESET", "\033[0m")
        full = f"{status} {name}".strip()
        bp = (bold_part or "").strip()
        if bp and full.startswith(bp):
            rest = full[len(bp):].lstrip()
            return f"{color}{bp}{RESET}{' ' + rest if rest else ''}{suffix}"
        if bp and name and name.strip().startswith(bp):
            bold_text = f"{status} {bp}".strip()
            rest = name.strip()[len(bp):].lstrip()
            return f"{color}{bold_text}{RESET}{' ' + rest if rest else ''}{suffix}"
        if name:
            return f"{color}{status}{RESET} {name}{suffix}"
        return f"{color}{status}{RESET}{suffix}"

    def refresh_stage(self, stage: TuringStage):
        """Refreshes the current active stage display line."""
        from logic.utils import log_debug
        log_debug(f"TM: refreshing stage '{stage.name}' (active_status: {stage.active_status}, active_name: {stage.active_name or stage.name})")
        
        if stage.stealth:
            return

        is_warning = (stage.success_color == "YELLOW" or stage.success_status == "Warning" or 
                      stage.active_status == "Warning" or stage.fail_color == "YELLOW")
        if self.no_warning and is_warning:
            return

        BOLD = get_color("BOLD", "\033[1m")
        active_name = stage.active_name if stage.active_name is not None else stage.name
        active_msg = self._format_msg(stage.active_status, active_name, BOLD,
                                       bold_part=stage.bold_part, suffix="...")
        self.manager.update(f"stage_{stage.name}", active_msg)

    def run(self, ephemeral: bool = False, final_newline: bool = False, final_msg: Optional[str] = None) -> bool:
        suppressor = get_global_suppressor()
        
        BOLD = get_color("BOLD", "\033[1m")
        get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")
        get_color("GREEN", "\033[32m")
        
        with suppressor:
            try:
                for i, stage in enumerate(self.stages):
                    if getattr(stage, "finished", False):
                        continue
                    stage.machine = self
                    
                    from logic.utils import log_debug
                    log_debug(f"TM: starting stage {i+1}/{len(self.stages)}: '{stage.name}' (active_status: {stage.active_status}, stealth: {stage.stealth})")
                    
                    is_last = (i == len(self.stages) - 1)
                    active_name = stage.active_name if stage.active_name is not None else stage.name
                    
                    is_warning = (stage.success_color == "YELLOW" or stage.success_status == "Warning" or 
                                  stage.active_status == "Warning" or stage.fail_color == "YELLOW")
                    
                    if not (self.no_warning and is_warning) and not stage.stealth:
                        suffix = "..." if not active_name.strip().endswith("...") else ""
                        active_msg = self._format_msg(
                            stage.active_status, active_name, BOLD,
                            bold_part=stage.bold_part, suffix=suffix)
                        self.manager.update(f"stage_{stage.name}", active_msg)
                    
                    try:
                        # Pass the stage itself to the action so it can report errors/output
                        # Support both Callable[[], bool] and Callable[[TuringStage], bool]
                        sig = inspect.signature(stage.action)
                        if len(sig.parameters) > 0:
                            success = stage.action(stage)
                        else:
                            success = stage.action()
                            
                        if success:
                            stage.finished = True
                            log_debug(f"TM: stage '{stage.name}' succeeded")
                            # Skip printing if it's a warning and no_warning is True, or if it's stealth
                            is_warning = (stage.success_color == "YELLOW" or stage.success_status == "Warning")
                            if (self.no_warning and is_warning) or stage.stealth:
                                # Just clear the active line and continue
                                if not ephemeral or not is_last:
                                    # Only update if it was actually added to manager (not stealthy)
                                    if f"stage_{stage.name}" in self.manager.worker_to_slot_idx:
                                        self.manager.update(f"stage_{stage.name}", "remove", is_final=True)
                                continue

                            # Use success_name if provided, else use name. 
                            # If success_name is explicitly "", use empty string.
                            success_name = stage.success_name if stage.success_name is not None else stage.name
                            color_code = get_color(stage.success_color, "\033[32m")
                            full_msg = self._format_msg(
                                stage.success_status, success_name or "", color_code,
                                bold_part=stage.bold_part)
                            
                            stripped_msg = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', full_msg)
                            if stripped_msg and not any(stripped_msg.rstrip().endswith(c) for c in [".", "!", ")", "]", "}", ">"]):
                                full_msg = full_msg.rstrip() + "."
                                
                            # Do NOT truncate finalized messages, allow them to wrap for visibility
                            # full_msg = truncate_to_width(full_msg, width)

                            if ephemeral:
                                if is_last and final_msg is not None:
                                    if final_msg == "":
                                        self.manager.update(f"stage_{stage.name}", "remove", is_final=True)
                                    else:
                                        self.manager.update(f"stage_{stage.name}", final_msg, is_final=True, truncate=False)
                                elif is_last and final_msg is None:
                                    self.manager.update(f"stage_{stage.name}", "remove", is_final=True)
                                elif is_last and not final_newline:
                                    self.manager.update(f"stage_{stage.name}", full_msg, is_final=True, truncate=False)
                                elif not stage.is_sticky and not is_last:
                                    self.manager.update(f"stage_{stage.name}", "remove", is_final=True)
                                else:
                                    self.manager.update(f"stage_{stage.name}", full_msg, is_final=True, truncate=False)
                            else:
                                self.manager.update(f"stage_{stage.name}", full_msg, is_final=True, truncate=False)
                        else:
                            # Failure
                            log_debug(f"TM: stage '{stage.name}' failed")
                            # Skip printing if it's a warning and no_warning is True
                            is_warning = (stage.fail_color == "YELLOW" or stage.fail_status == "Warning")
                            if self.no_warning and is_warning:
                                if f"stage_{stage.name}" in self.manager.worker_to_slot_idx:
                                    self.manager.update(f"stage_{stage.name}", "remove", is_final=True)
                                return True

                            if stage.stealth:
                                if f"stage_{stage.name}" in self.manager.worker_to_slot_idx:
                                    self.manager.update(f"stage_{stage.name}", "remove", is_final=True)
                                return False
                            
                            log_path = self._log_error(stage)
                            if f"stage_{stage.name}" in self.manager.worker_to_slot_idx:
                                self.manager.update(f"stage_{stage.name}", "remove", is_final=True)
                            
                            fail_name = stage.fail_name if stage.fail_name is not None else stage.name
                            brief_reason = stage.error_brief
                            
                            if not brief_reason:
                                if stage.error_full and isinstance(stage.error_full, str):
                                    # Try to extract the first line or a specific "error:" pattern from error_full
                                    lines = stage.error_full.splitlines()
                                    error_line = next((l for l in lines if "error:" in l.lower()), None)
                                    if error_line:
                                        brief_reason = error_line.strip()
                                    elif lines:
                                        brief_reason = lines[0].strip()
                                    else:
                                        brief_reason = "Action returned False"
                                else:
                                    brief_reason = "Action returned False"
                            
                            if self.no_warning and is_warning:
                                return True 
                            
                            fail_color_code = get_color(stage.fail_color, "\033[31m")
                            DIM = get_color("DIM", "\033[2m")
                            fail_msg_start = self._format_msg(
                                stage.fail_status, fail_name or "", fail_color_code,
                                bold_part=stage.bold_part)
                            
                            brief_reason = brief_reason.rstrip(".")
                            
                            logic_dir = str(find_project_root(Path(__file__)) / "logic")
                            if fail_name == "":
                                full_msg_fail = f"{fail_msg_start}."
                            else:
                                reason_label = get_translation(logic_dir, "label_reason", "Reason")
                                full_msg_fail = f"{fail_msg_start}."
                            
                            self.manager.update(f"stage_{stage.name}", full_msg_fail, is_final=True, truncate=False)
                            if brief_reason:
                                reason_label = get_translation(logic_dir, "label_reason", "Reason")
                                self.manager.update(f"reason_{stage.name}", f"  {DIM}{reason_label}: {brief_reason}.{RESET}", is_final=True, truncate=False)
                            if log_path:
                                traceback_label = get_translation(logic_dir, "label_traceback_saved_to", "Traceback saved to")
                                self.manager.update(f"log_{stage.name}", f"  {DIM}{traceback_label}: {log_path}{RESET}", is_final=True, truncate=False)
                            
                            return False
                    except Exception as e:
                        from logic.turing.logic import TuringError
                        if isinstance(e, TuringError):
                            stage.error_brief = e.brief
                            stage.error_full = e.full
                        
                        log_path = self._log_error(stage, exception=e if not isinstance(e, TuringError) else None)
                        if f"stage_{stage.name}" in self.manager.worker_to_slot_idx:
                            self.manager.update(f"stage_{stage.name}", "remove", is_final=True)
                        
                        fail_name = stage.fail_name if stage.fail_name is not None else stage.name
                        brief_reason = stage.error_brief or str(e).split('\n')[0]
                        brief_reason = brief_reason.rstrip(".")
                        
                        fail_color_code = get_color(stage.fail_color, "\033[31m")
                        DIM = get_color("DIM", "\033[2m")
                        fail_msg_start = self._format_msg(
                            stage.fail_status, fail_name or "", fail_color_code,
                            bold_part=stage.bold_part)
                        
                        logic_dir = str(find_project_root(Path(__file__)) / "logic")
                        fail_msg = f"{fail_msg_start}."
                        self.manager.update(f"stage_{stage.name}", fail_msg, is_final=True, truncate=False)
                        if brief_reason:
                            reason_label = get_translation(logic_dir, "label_reason", "Reason")
                            self.manager.update(f"reason_{stage.name}", f"  {DIM}{reason_label}: {brief_reason}.{RESET}", is_final=True, truncate=False)
                        if log_path:
                            traceback_label = get_translation(logic_dir, "label_traceback_saved_to", "Traceback saved to")
                            self.manager.update(f"log_{stage.name}", f"  {DIM}{traceback_label}: {log_path}{RESET}", is_final=True, truncate=False)
                        
                        return False
                
                if ephemeral:
                    for stage in self.stages:
                        key = f"stage_{stage.name}"
                        if key in self.manager.worker_to_slot_idx:
                            self.manager.update(key, "remove", is_final=True)
                
                # If non-ephemeral, the last stage already printed a newline
                return True
            except KeyboardInterrupt:
                if suppressor:
                    try: suppressor.stop(force=True)
                    except: pass
                
                BOLD_RED = "\033[1;31m"
                RESET = "\033[0m"
                
                # Remove all active stage lines from the display
                for s in self.stages:
                    key = f"stage_{s.name}"
                    if key in self.manager.worker_to_slot_idx:
                        self.manager.update(key, "remove", is_final=True)
                
                # Try to get translation, but have a solid fallback
                try:
                    root = find_project_root(Path(__file__))
                    logic_dir = str(get_logic_dir(root))
                    cancelled_label = get_translation(logic_dir, "msg_operation_cancelled", "Operation cancelled")
                    by_user_label = get_translation(logic_dir, "msg_cancelled_by_user", "by user.")
                except:
                    cancelled_label, by_user_label = "Operation cancelled", "by user."
                
                sys.stdout.write(f"{BOLD_RED}{cancelled_label}{RESET} {by_user_label}\n")
                sys.stdout.flush()
                
                # Force exit to prevent being caught and ignored by other loops
                os._exit(130)
            except Exception:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                raise
