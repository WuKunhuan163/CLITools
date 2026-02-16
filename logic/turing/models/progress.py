import sys
from typing import List, Optional
from logic.turing.logic import TuringStage

class ProgressTuringMachine:
    """Executes a sequence of TuringStages with erasable progress display."""
    def __init__(self, stages: List[TuringStage] = None, project_root: Optional[str] = None, 
                 tool_name: Optional[str] = None, log_dir: Optional[str] = None,
                 no_warning: bool = False):
        self.stages = stages or []
        self.no_warning = no_warning
        # Support for error logging
        from pathlib import Path
        self.project_root = Path(project_root) if project_root else None
        self.tool_name = tool_name
        self.log_dir = Path(log_dir) if log_dir else None

    def add_stage(self, stage: TuringStage):
        self.stages.append(stage)
        
    def _log_error(self, stage: TuringStage, exception: Optional[Exception] = None):
        """Saves full error information to a log file."""
        from logic.turing.utils import log_turing_error
        return log_turing_error(stage, self.project_root, self.tool_name, exception, log_dir=self.log_dir)

    def refresh_stage(self, stage: TuringStage):
        """Refreshes the current active stage display line."""
        if stage.stealth:
            return

        # Detect if this stage is a warning
        is_warning = (stage.success_color == "YELLOW" or stage.success_status == "Warning" or 
                      stage.active_status == "Warning" or stage.fail_color == "YELLOW")
        
        if self.no_warning and is_warning:
            return

        from logic.config import get_color
        from logic.turing.display.manager import truncate_to_width, _get_configured_width
        
        BLUE = get_color("BLUE", "\033[34m")
        BOLD = get_color("BOLD", "\033[1m")
        RESET = get_color("RESET", "\033[0m")
        
        width = _get_configured_width()
        active_name = stage.active_name or stage.name
        
        if stage.bold_part and active_name.startswith(stage.bold_part):
            bold_text = f"{stage.active_status} {stage.bold_part}"
            rest_text = active_name[len(stage.bold_part):].lstrip()
            active_msg = f"{BOLD}{BLUE}{bold_text}{RESET} {rest_text}..."
        else:
            active_msg = f"{BOLD}{BLUE}{stage.active_status}{RESET} {active_name}..."
        
        sys.stdout.write(f"\r\033[K{truncate_to_width(active_msg, width)}")
        sys.stdout.flush()

    def run(self, ephemeral: bool = False, final_newline: bool = True, final_msg: Optional[str] = None) -> bool:
        from logic.config import get_color
        from logic.turing.display.manager import truncate_to_width, _get_configured_width
        from logic.terminal.keyboard import KeyboardSuppressor
        import traceback
        
        BLUE = get_color("BLUE", "\033[34m")
        BOLD = get_color("BOLD", "\033[1m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")
        GREEN = get_color("GREEN", "\033[32m")
        
        with KeyboardSuppressor():
            try:
                for i, stage in enumerate(self.stages):
                    # Attach machine to stage so action can refresh
                    stage.machine = self
                    
                    is_last = (i == len(self.stages) - 1)
                    active_name = stage.active_name or stage.name
                    width = _get_configured_width()
                    
                    # Detect if this stage is a warning
                    is_warning = (stage.success_color == "YELLOW" or stage.success_status == "Warning" or 
                                  stage.active_status == "Warning" or stage.fail_color == "YELLOW")
                    
                    if not (self.no_warning and is_warning) and not stage.stealth:
                        if stage.bold_part and active_name.startswith(stage.bold_part):
                            bold_text = f"{stage.active_status} {stage.bold_part}"
                            rest_text = active_name[len(stage.bold_part):].lstrip()
                            active_msg = f"{BOLD}{BLUE}{bold_text}{RESET} {rest_text}..."
                        else:
                            active_msg = f"{BOLD}{BLUE}{stage.active_status}{RESET} {active_name}..."
                        
                        sys.stdout.write(f"\r\033[K{truncate_to_width(active_msg, width)}")
                        sys.stdout.flush()
                    
                    try:
                        # Pass the stage itself to the action so it can report errors/output
                        # Support both Callable[[], bool] and Callable[[TuringStage], bool]
                        import inspect
                        sig = inspect.signature(stage.action)
                        if len(sig.parameters) > 0:
                            success = stage.action(stage)
                        else:
                            success = stage.action()
                            
                        if success:
                            # Skip printing if it's a warning and no_warning is True, or if it's stealth
                            is_warning = (stage.success_color == "YELLOW" or stage.success_status == "Warning")
                            if (self.no_warning and is_warning) or stage.stealth:
                                # Just clear the active line and continue
                                if not ephemeral or not is_last:
                                    sys.stdout.write("\r\033[K")
                                    sys.stdout.flush()
                                continue

                            # Use success_name if provided, else use name. 
                            # If success_name is explicitly "", use empty string.
                            if stage.success_name is not None:
                                success_name = stage.success_name
                            else:
                                success_name = stage.name
                                
                            color_code = get_color(stage.success_color, "\033[32m")
                            if stage.bold_part and success_name and success_name.startswith(stage.bold_part):
                                bold_text = f"{stage.success_status} {stage.bold_part}"
                                rest_text = success_name[len(stage.bold_part):].lstrip()
                                full_msg = f"{BOLD}{color_code}{bold_text}{RESET} {rest_text}"
                            elif success_name:
                                full_msg = f"{BOLD}{color_code}{stage.success_status}{RESET} {success_name}"
                            else:
                                # Explicitly empty success_name
                                full_msg = f"{BOLD}{color_code}{stage.success_status}{RESET}"
                                
                            full_msg = truncate_to_width(full_msg, width)
                            
                            if ephemeral:
                                if is_last and final_msg is not None:
                                    sys.stdout.write(f"\r\033[K{truncate_to_width(final_msg, width)}")
                                elif is_last and not final_newline:
                                    sys.stdout.write(f"\r\033[K{full_msg}")
                                elif not stage.is_sticky and not is_last:
                                    sys.stdout.write(f"\r\033[K{full_msg}")
                                else:
                                    sys.stdout.write(f"\r\033[K{full_msg}\n")
                            else:
                                sys.stdout.write(f"\r\033[K{full_msg}\n")
                            sys.stdout.flush()
                        else:
                            # Failure
                            # Skip printing if it's a warning and no_warning is True
                            is_warning = (stage.fail_color == "YELLOW" or stage.fail_status == "Warning")
                            if self.no_warning and is_warning:
                                # Just clear the active line and continue
                                sys.stdout.write("\r\033[K")
                                sys.stdout.flush()
                                return True # Continue the pipeline if it was just a warning? No, usually action returning False means stop. But for warning, maybe we want to continue?
                                # Actually, for warning, if it fails, it might still mean something went wrong. 
                                # But the user wants to filter out WARNING information.
                                # I'll return True to allow the sequence to continue if it was just a warning failure.
                                # Wait, if it was a failure, maybe we should still stop but just not print it?
                                # Re-reading: "过滤掉图灵机输出所有的Warning信息"
                                # I'll return success=True if it was a warning failure and no_warning is active.
                            
                            log_path = self._log_error(stage)
                            sys.stdout.write("\r\033[K")
                            sys.stdout.flush()
                            
                            fail_name = stage.fail_name or stage.name
                            brief_reason = stage.error_brief or "Action returned False"
                            
                            # If we have a full error log, prioritize it for the brief if it's a string
                            if stage.error_full and isinstance(stage.error_full, str) and not stage.error_brief:
                                brief_reason = stage.error_full
                            
                            if self.no_warning and is_warning:
                                # Just clear the active line and continue
                                sys.stdout.write("\r\033[K")
                                sys.stdout.flush()
                                return True 
                            
                            fail_color_code = get_color(stage.fail_color, "\033[31m")
                            
                            if stage.bold_part and fail_name.startswith(stage.bold_part):
                                bold_text = f"{stage.fail_status} {stage.bold_part}"
                                rest_text = fail_name[len(stage.bold_part):].lstrip()
                                full_msg_fail = f"{BOLD}{fail_color_code}{bold_text}{RESET} {rest_text}"
                            else:
                                full_msg_fail = f"{BOLD}{fail_color_code}{stage.fail_status}{RESET} {fail_name}"
                            
                            # Ensure we don't have double periods
                            brief_reason = brief_reason.rstrip(".")
                            full_msg_fail += f". Reason: {brief_reason}."
                            
                            sys.stdout.write(f"\r\033[K{full_msg_fail}\n")
                            if log_path:
                                print(f"{BOLD}Traceback saved to:{RESET} {log_path}", flush=True)
                                
                            sys.stdout.flush()
                            return False
                    except Exception as e:
                        # Handle TuringError or other exceptions
                        from logic.turing.logic import TuringError
                        if isinstance(e, TuringError):
                            stage.error_brief = e.brief
                            stage.error_full = e.full
                        
                        log_path = self._log_error(stage, exception=e if not isinstance(e, TuringError) else None)
                        sys.stdout.write("\r\033[K")
                        sys.stdout.flush()
                        
                        fail_name = stage.fail_name or stage.name
                        brief_reason = stage.error_brief or str(e).split('\n')[0]
                        brief_reason = brief_reason.rstrip(".")
                        
                        fail_color_code = get_color(stage.fail_color, "\033[31m")
                        
                        if stage.bold_part and fail_name.startswith(stage.bold_part):
                            bold_text = f"{stage.fail_status} {stage.bold_part}"
                            rest_text = fail_name[len(stage.bold_part):].lstrip()
                            fail_msg = f"{BOLD}{fail_color_code}{bold_text}{RESET} {rest_text}. Reason: {brief_reason}."
                        else:
                            fail_msg = f"{BOLD}{fail_color_code}{stage.fail_status}{RESET} {fail_name}. Reason: {brief_reason}."
                        sys.stdout.write(f"\r\033[K{fail_msg}\n")
                        if log_path:
                            print(f"{BOLD}Traceback saved to:{RESET} {log_path}", flush=True)
                            
                        sys.stdout.flush()
                        return False
                
                if ephemeral and final_newline:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                return True
            except KeyboardInterrupt:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                # Print cancellation status
                BOLD = get_color("BOLD", "\033[1m")
                YELLOW = get_color("YELLOW", "\033[33m")
                RESET = get_color("RESET", "\033[0m")
                sys.stdout.write(f"{BOLD}{YELLOW}Cancelled{RESET} Operation cancelled by user.\n")
                sys.stdout.flush()
                raise
            except Exception:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                raise
