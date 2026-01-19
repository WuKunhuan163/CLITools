import sys
from typing import List
from logic.turing.logic import TuringStage

class ProgressTuringMachine:
    """Executes a sequence of TuringStages with erasable progress display."""
    def __init__(self, stages: List[TuringStage] = None):
        self.stages = stages or []
        
    def add_stage(self, stage: TuringStage):
        self.stages.append(stage)
        
    def run(self, ephemeral: bool = False, final_newline: bool = True) -> bool:
        from logic.config import get_color
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
                    # Clear the "Running..." line before printing failure to ensure it's clean
                    sys.stdout.write(f"\r\033[K")
                    sys.stdout.flush()
                    fail_name = stage.fail_name or stage.name
                    # Color the entire status prefix as bold red
                    sys.stdout.write(f"{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}\n")
                    sys.stdout.flush()
                    return False
            except Exception as e:
                # Clear the "Running..." line before printing error
                sys.stdout.write(f"\r\033[K")
                sys.stdout.flush()
                fail_name = stage.fail_name or stage.name
                # Color the entire status prefix as bold red
                sys.stdout.write(f"{BOLD}{RED}{stage.fail_status}{RESET} {fail_name}: {e}\n")
                sys.stdout.flush()
                return False
        
        if ephemeral and final_newline:
            # We don't want a newline here if we want the final message to overwrite the last stage
            pass
            
        return True

