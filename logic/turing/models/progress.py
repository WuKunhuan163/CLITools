import sys
from typing import List, Optional
from logic.turing.logic import TuringStage

class ProgressTuringMachine:
    """Executes a sequence of TuringStages with erasable progress display."""
    def __init__(self, stages: List[TuringStage] = None, project_root: Optional[str] = None, tool_name: Optional[str] = None):
        self.stages = stages or []
        # Support for error logging
        from pathlib import Path
        self.project_root = Path(project_root) if project_root else None
        self.tool_name = tool_name

    def add_stage(self, stage: TuringStage):
        self.stages.append(stage)
        
    def _log_error(self, stage: TuringStage, exception: Optional[Exception] = None):
        """Saves full error information to a log file."""
        if not self.project_root or not self.tool_name: return
        
        import time
        import traceback
        from pathlib import Path
        
        log_dir = self.project_root / "data" / "log" / self.tool_name
        log_dir.mkdir(parents=True, exist_ok=True)
        
        ts = time.strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"fail_{ts}.log"
        
        full_info = stage.error_full or (str(exception) if exception else "Unknown failure")
        if exception:
            full_info += "\n\nTraceback:\n" + traceback.format_exc()
            
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Stage: {stage.name}\n")
                f.write(f"Timestamp: {ts}\n")
                f.write("-" * 20 + "\n")
                f.write(full_info)
            
            # Basic cleanup (limit 100 logs)
            from logic.utils import cleanup_old_files
            cleanup_old_files(log_dir, "fail_*.log", limit=100)
            return log_file
        except: return None

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
                    is_last = (i == len(self.stages) - 1)
                    active_name = stage.active_name or stage.name
                    width = _get_configured_width()
                    active_msg = f"{BOLD}{BLUE}{stage.active_status}{RESET} {active_name}..."
                    sys.stdout.write(f"\r\033[K{truncate_to_width(active_msg, width)}")
                    sys.stdout.flush()
                    
                    try:
                        success = stage.action()
                        if success:
                            # ... (success logic) ...
                            success_name = stage.success_name or stage.name
                            color_code = get_color(stage.success_color, "\033[32m")
                            if stage.bold_part and success_name.startswith(stage.bold_part):
                                bold_text = f"{stage.success_status} {stage.bold_part}"
                                rest_text = success_name[len(stage.bold_part):].lstrip()
                                full_msg = f"{BOLD}{color_code}{bold_text}{RESET} {rest_text}"
                            else:
                                full_msg = f"{BOLD}{color_code}{stage.success_status}{RESET} {success_name}"
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
                            log_path = self._log_error(stage)
                            sys.stdout.write("\r\033[K")
                            sys.stdout.flush()
                            
                            fail_name = stage.fail_name or stage.name
                            brief_reason = stage.error_brief or "Action returned False"
                            
                            if stage.bold_part and fail_name.startswith(stage.bold_part):
                                bold_text = f"{stage.fail_status} {stage.bold_part}"
                                rest_text = fail_name[len(stage.bold_part):].lstrip()
                                full_msg_fail = f"{BOLD}{RED}{bold_text}{RESET} {rest_text}"
                            else:
                                full_msg_fail = f"{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}"
                            
                            full_msg_fail += f". Reason: {brief_reason}"
                            sys.stdout.write(f"\r\033[K{full_msg_fail}\n")
                            if log_path:
                                log_msg = f"{BOLD}Traceback saved to{RESET}: {log_path}"
                                sys.stdout.write(f"{log_msg}\n")
                                
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
                        
                        fail_msg = f"{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}. Reason: {brief_reason}"
                        sys.stdout.write(f"{fail_msg}\n")
                        if log_path:
                            log_msg = f"{BOLD}Traceback saved to{RESET}: {log_path}"
                            sys.stdout.write(f"{log_msg}\n")
                            
                        sys.stdout.flush()
                        return False
                
                if ephemeral and final_newline:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                return True
            except (KeyboardInterrupt, Exception):
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                raise
