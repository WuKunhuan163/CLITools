import sys
from pathlib import Path
import argparse
import os
import pickle

# Add project root to sys.path
script_path = Path(__file__).resolve()
# tool/iCloud/logic/gui/login.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.two_step_login.gui import TwoStepLoginWindow

class ICloudLoginWindow(TwoStepLoginWindow):
    """
    Customized login window for iCloud using the two_step_login blueprint.
    """
    def __init__(self, title, timeout, internal_dir, error_msg=None, verify_handler=None):
        super().__init__(
            title, timeout, internal_dir, 
            tool_name="iCloud",
            error_msg=error_msg,
            verify_handler=verify_handler
        )

    def get_current_state(self):
        """Standardize on 'account' field for blueprint compatibility."""
        return super().get_current_state()

    def setup_ui(self):
        """Override labels using iCloud-specific translations before building UI."""
        self.instruction_text = self._("login_instruction", "Sign in to iCloud")
        self.account_label_text = self._("label_apple_id", "Apple ID:")
        self.password_label_text = self._("label_password", "Password:")
        super().setup_ui()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="iCloud Login")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--internal-dir")
    args = parser.parse_args()

    from logic.gui.engine import setup_gui_environment, get_safe_python_for_gui
    import subprocess

    # Auto-reexecute with safe python if current one lacks tkinter
    try:
        import _tkinter
    except ImportError:
        py_exe = get_safe_python_for_gui()
        if py_exe and py_exe != sys.executable:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)
            sys.exit(subprocess.call([py_exe, __file__] + sys.argv[1:], env=env))
        else:
            sys.exit("Error: Tkinter not found.")

    setup_gui_environment()

    # Read from environment variables if set (managed mode)
    apple_id = os.environ.get("GDS_LOGIN_APPLE_ID")
    error_msg = os.environ.get("GDS_LOGIN_ERROR")

    def icloud_verify_handler(state):
        from pyicloud import PyiCloudService
        from pyicloud.exceptions import PyiCloudFailedLoginException, PyiCloudAPIResponseException
        
        apple_id = state.get("account")
        password = state.get("password")
        step = state.get("step")
        
        # Determine cookie file path
        # In this project, iCloudPD data resides in tool/iCloud/tool/iCloudPD/data/session/<apple_id>/
        cookie_dir = project_root / "tool" / "iCloud" / "tool" / "iCloudPD" / "data" / "session" / apple_id
        cookie_dir.mkdir(parents=True, exist_ok=True)
        cookie_file = cookie_dir / "session.pkl"

        if step == "account":
            # Step 1: Try session reuse
            if cookie_file.exists():
                try:
                    # Initialize without password
                    api = PyiCloudService(apple_id, "")
                    # Load cookies
                    with open(cookie_file, 'rb') as f:
                        api.session.cookies.update(pickle.load(f))
                    # Verify session validity
                    _ = api.account.devices
                    return {"status": "success", "data": {"apple_id": apple_id, "mode": "session_reuse"}}
                except:
                    # Cookie expired or invalid
                    pass
            return {"status": "need_password"}
        else:
            # Step 2: Full login
            try:
                api = PyiCloudService(apple_id, password)
                # Success! Save cookies for next time
                with open(cookie_file, 'wb') as f:
                    pickle.dump(api.session.cookies, f)
                return {"status": "success", "data": {"apple_id": apple_id, "password": password, "mode": "full_login"}}
            except (PyiCloudFailedLoginException, PyiCloudAPIResponseException) as e:
                msg = str(e)
                if "locked" in msg.lower() or "-20209" in msg:
                    msg = "Account locked. Visit https://iforgot.apple.com to reset."
                return {"status": "error", "message": msg}
            except Exception as e:
                return {"status": "error", "message": f"System error: {str(e)}"}

    # If internal_dir is not provided, use the script's directory
    internal_dir = args.internal_dir
    if not internal_dir:
        internal_dir = str(Path(__file__).resolve().parent)

    win = ICloudLoginWindow(args.title, args.timeout, internal_dir, 
                            error_msg=error_msg, verify_handler=icloud_verify_handler)
    if apple_id:
        win.account_initial = apple_id
    win.run(win.setup_ui)
