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
        from logic.turing.display.manager import truncate_to_width, _get_configured_width
        from logic.terminal.keyboard import KeyboardSuppressor
        
        BLUE = get_color("BLUE", "\033[34m")
        BOLD = get_color("BOLD", "\033[1m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")
        GREEN = get_color("GREEN", "\033[32m")
        
        with KeyboardSuppressor():
            try:
                for i, stage in enumerate(self.stages):
                    is_last = (i == len(self.stages) - 1)
                    # Show active status - entire status prefix is now bold blue
                    active_name = stage.active_name or stage.name
                    
                    # Truncate to avoid line wrapping which breaks \r\033[K
                    width = _get_configured_width()
                    active_msg = f"{BOLD}{BLUE}{stage.active_status}{RESET} {active_name}..."
                    sys.stdout.write(f"\r\033[K{truncate_to_width(active_msg, width)}")
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
                            
                            # Truncate success message as well
                            full_msg = truncate_to_width(full_msg, width)
                            
                            if ephemeral:
                                if is_last and final_msg is not None:
                                    # Overwrite the last stage with final_msg
                                    sys.stdout.write(f"\r\033[K{truncate_to_width(final_msg, width)}")
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
                            # 1. Clear current line
                            sys.stdout.write("\r\033[K")
                            sys.stdout.flush()
                            
                            if not ephemeral:
                                # Standard failure display
                                fail_name = stage.fail_name or stage.name
                                if stage.bold_part and fail_name.startswith(stage.bold_part):
                                    bold_text = f"{stage.fail_status} {stage.bold_part}"
                                    rest_text = fail_name[len(stage.bold_part):].lstrip()
                                    full_msg_fail = f"{BOLD}{RED}{bold_text}{RESET} {rest_text}"
                                else:
                                    full_msg_fail = f"{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}"
                                sys.stdout.write(f"{truncate_to_width(full_msg_fail, width)}\n")
                            
                            sys.stdout.flush()
                            return False
                    except Exception as e:
                        # 1. Clear current line
                        sys.stdout.write("\r\033[K")
                        sys.stdout.flush()
                        
                        if not ephemeral:
                            fail_name = stage.fail_name or stage.name
                            fail_msg = f"{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}: {e}"
                            sys.stdout.write(f"{truncate_to_width(fail_msg, width)}\n")
                        
                        sys.stdout.flush()
                        return False
                
                if ephemeral and final_newline:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    
                return True
            except (KeyboardInterrupt, Exception):
                # Ensure the current line is cleared on any top-level exit
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                raise
