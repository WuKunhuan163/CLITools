import sys
from typing import List, Optional
from logic.turing.logic import TuringStage

class ProgressTuringMachine:
    """Executes a sequence of TuringStages with erasable progress display."""
    def __init__(self, stages: List[TuringStage] = None):
        self.stages = stages or []
        
    def add_stage(self, stage: TuringStage):
        self.stages.append(stage)
        
    def run(self, ephemeral: bool = False, final_newline: bool = True, final_msg: Optional[str] = None) -> bool:
        from logic.config import get_color
        BLUE = get_color("BLUE", "\033[34m")
        BOLD = get_color("BOLD", "\033[1m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")
        GREEN = get_color("GREEN", "\033[32m")
        
        for i, stage in enumerate(self.stages):
            is_last = (i == len(self.stages) - 1)
            # Show active status - entire status prefix is now bold blue
            active_name = stage.active_name or stage.name
            sys.stdout.write(f"\r\033[K{BOLD}{BLUE}{stage.active_status}{RESET} {active_name}...")
            sys.stdout.flush()
            
            try:
                success = stage.action()
                if success:
                    success_name = stage.success_name or stage.name
                    color_code = get_color(stage.success_color, "\033[32m")
                    
                    # Split success_name into bold and normal parts
                    if stage.bold_part and success_name.startswith(stage.bold_part):
                        bold_text = f"{stage.success_status} {stage.bold_part}"
                        rest_text = success_name[len(stage.bold_part):].lstrip()
                        full_msg = f"{BOLD}{color_code}{bold_text}{RESET} {rest_text}"
                    else:
                        # Default: Only success_status is bolded
                        full_msg = f"{BOLD}{color_code}{stage.success_status}{RESET} {success_name}"
                    
                    if ephemeral:
                        if is_last and final_msg is not None:
                            # Overwrite the last stage with final_msg
                            sys.stdout.write(f"\r\033[K{final_msg}")
                        elif is_last and not final_newline:
                            # Print last stage without newline
                            sys.stdout.write(f"\r\033[K{full_msg}")
                        elif not stage.is_sticky and not is_last:
                            # Intermediate stage, no newline
                            sys.stdout.write(f"\r\033[K{full_msg}")
                        else:
                            # Sticky or last stage with newline
                            sys.stdout.write(f"\r\033[K{full_msg}\n")
                    else:
                        sys.stdout.write(f"\r\033[K{full_msg}\n")
                    sys.stdout.flush()
                else:
                    # ... failure handling ...
                    sys.stdout.write(f"\r\033[K")
                    sys.stdout.flush()
                    fail_name = stage.fail_name or stage.name
                    
                    if stage.bold_part and fail_name.startswith(stage.bold_part):
                        bold_text = f"{stage.fail_status} {stage.bold_part}"
                        rest_text = fail_name[len(stage.bold_part):].lstrip()
                        full_msg_fail = f"{BOLD}{RED}{bold_text}{RESET} {rest_text}"
                    else:
                        full_msg_fail = f"{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}"
                        
                    sys.stdout.write(f"{full_msg_fail}\n")
                    sys.stdout.flush()
                    return False
            except Exception as e:
                # ... error handling ...
                sys.stdout.write(f"\r\033[K")
                sys.stdout.flush()
                fail_name = stage.fail_name or stage.name
                sys.stdout.write(f"{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}: {e}\n")
                sys.stdout.flush()
                return False
        
        # Ensure exactly one newline at the end if requested
        if ephemeral and final_newline:
            # If final_msg was printed without newline (Line 46), add it now.
            # If last stage was sticky, it already printed a newline (Line 55).
            # If last stage was not sticky but final_newline is true, it printed a newline (Line 55).
            # Wait, Line 55 is executed for is_last AND final_newline=True.
            pass
            
        return True

