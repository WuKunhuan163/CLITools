import sys
from typing import List
from proj.turing.core import TuringStage

class ProgressTuringMachine:
    """Executes a sequence of TuringStages with erasable progress display."""
    def __init__(self, stages: List[TuringStage] = None):
        self.stages = stages or []
        
    def add_stage(self, stage: TuringStage):
        self.stages.append(stage)
        
    def run(self, ephemeral: bool = False, final_newline: bool = True) -> bool:
        from proj.config import get_color
        BLUE = get_color("BLUE", "\033[34m")
        BOLD = get_color("BOLD", "\033[1m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")
        
        for stage in self.stages:
            # Show active status - entire status prefix is now bold blue
            active_name = stage.active_name or stage.name
            sys.stdout.write(f"\r\033[K{BOLD}{BLUE}{stage.active_status}{RESET} {active_name}...")
            sys.stdout.flush()
            
            try:
                success = stage.action()
                if success:
                    success_name = stage.success_name or stage.name
                    color = get_color(stage.success_color, "\033[32m")
                    if ephemeral and not stage.is_sticky:
                        # Success message but no newline, ready to be overwritten by next stage
                        sys.stdout.write(f"\r\033[K{BOLD}{color}{stage.success_status}{RESET} {success_name}")
                    else:
                        sys.stdout.write(f"\r\033[K{BOLD}{color}{stage.success_status}{RESET} {success_name}\n")
                    sys.stdout.flush()
                else:
                    fail_name = stage.fail_name or stage.name
                    sys.stdout.write(f"\r\033[K{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}\n")
                    sys.stdout.flush()
                    return False
            except Exception as e:
                fail_name = stage.fail_name or stage.name
                sys.stdout.write(f"\r\033[K{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}: {e}\n")
                sys.stdout.flush()
                return False
        
        if ephemeral and final_newline:
            # We don't want a newline here if we want the final message to overwrite the last stage
            pass
            
        return True

