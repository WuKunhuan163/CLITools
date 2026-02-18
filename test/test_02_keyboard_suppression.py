import sys
import os
import time
import signal
import threading
from pathlib import Path

# EXPECTED_CPU_LIMIT = 80.0

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage
from logic.terminal.keyboard import get_global_suppressor

def test_keyboard_suppression_release():
    """
    Verifies that keyboard suppression is correctly released when a 
    ProgressTuringMachine is interrupted by a KeyboardInterrupt (SIGINT).
    """
    print("Testing keyboard suppression release on interrupt...")
    
    suppressor = get_global_suppressor()
    
    # Ensure suppressor is NOT running initially
    if suppressor.running:
        print("Pre-test cleanup: Stopping active suppressor...")
        suppressor.stop(force=True)
    
    def long_action(stage=None):
        # Action that waits to be interrupted
        # Use a loop to keep checking if we should exit
        start = time.time()
        while time.time() - start < 5:
            time.sleep(0.1)
        return True

    pm = ProgressTuringMachine([
        TuringStage("Interruptible Task", long_action)
    ])

    # Thread to send SIGINT after 1s
    def trigger_interrupt():
        time.sleep(1)
        print("\n[Test] Sending SIGINT to simulate Ctrl+C...")
        os.kill(os.getpid(), signal.SIGINT)

    interrupter = threading.Thread(target=trigger_interrupt, daemon=True)
    interrupter.start()

    try:
        # Run the machine. It will be interrupted.
        # Use stealth=True for the machine to avoid excessive output in tests
        pm.run()
    except KeyboardInterrupt:
        print("[Test] Caught KeyboardInterrupt.")
    
    # Verify suppressor state
    is_running = suppressor.running
    ref_count = suppressor._ref_count
    
    print(f"Post-interrupt status:")
    print(f"  - Suppressor running: {is_running}")
    print(f"  - Ref count: {ref_count}")
    
    if is_running:
        print("FAILURE: Keyboard suppression is still active after interruption!")
        return False
    if ref_count != 0:
        print(f"FAILURE: Reference count is {ref_count} (expected 0)!")
        return False
        
    print("SUCCESS: Keyboard suppression was correctly released.")
    return True

if __name__ == "__main__":
    if test_keyboard_suppression_release():
        sys.exit(0)
    else:
        sys.exit(1)


