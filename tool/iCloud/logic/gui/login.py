import sys
from pathlib import Path
import argparse

# Add project root to sys.path
script_path = Path(__file__).resolve()
# tool/iCloud/logic/gui/login.py -> 4 levels up to project root
project_root = script_path.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.account_login.gui import AccountLoginWindow

class ICloudLoginWindow(AccountLoginWindow):
    """
    Customized login window for iCloud using the account_login blueprint.
    """
    def __init__(self, title, timeout, internal_dir):
        super().__init__(
            title, timeout, internal_dir, 
            tool_name="iCloud"
        )

    def get_current_state(self):
        """Map generic account field to apple_id for iCloud tool compatibility."""
        state = super().get_current_state()
        return {
            "apple_id": state["account"],
            "password": state["password"]
        }

    def setup_ui(self):
        """Override labels using iCloud-specific translations before building UI."""
        self.instruction_text = self._("login_instruction", "Sign in to iCloud")
        self.account_label = self._("label_apple_id", "Apple ID:")
        self.password_label = self._("label_password", "Password:")
        super().setup_ui()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="iCloud Login")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--internal-dir")
    args = parser.parse_args()

    from logic.gui.engine import setup_gui_environment
    setup_gui_environment()

    win = ICloudLoginWindow(args.title, args.timeout, args.internal_dir)
    win.run(win.setup_ui)
