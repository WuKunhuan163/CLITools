#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
import argparse
import subprocess
import json
import os
import time
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Debugging imports
try:
    import logic
    # print(f"DEBUG: logic location: {logic.__file__}")
except ImportError:
    # print("DEBUG: logic not found in sys.path")
    pass

from logic.tool.base import ToolBase
from logic.config import get_color
from logic.gui.engine import get_safe_python_for_gui

# Global colors
BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
BLUE = get_color("BLUE")
RED = get_color("RED")
YELLOW = get_color("YELLOW")
RESET = get_color("RESET")

class ICloudTool(ToolBase):
    def __init__(self):
        super().__init__("iCloud")
        self.internal_dir = self.script_dir / "logic"

    def run_login_gui(self):
        python_exe = get_safe_python_for_gui()
        login_script = self.internal_dir / "gui" / "login.py"
        
        cmd = [
            python_exe, str(login_script),
            "--title", self.get_translation("btn_login", "iCloud Login"),
            "--internal-dir", str(self.internal_dir)
        ]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        stdout, stderr = process.communicate()
        
        result = None
        for line in stdout.splitlines():
            if line.startswith("GDS_GUI_RESULT_JSON:"):
                try:
                    result = json.loads(line[len("GDS_GUI_RESULT_JSON:"):])
                except:
                    pass
                break
        
        if result and result.get("status") == "success":
            return result["data"]
        
        if result and result.get("status") == "cancelled":
            msg = self.get_translation("msg_login_cancelled", "Login cancelled by user.")
            print(f"{BOLD}{YELLOW}{msg}{RESET}")
        elif result and result.get("status") == "timeout":
            msg = self.get_translation("msg_login_timeout", "Login timed out.")
            print(f"{BOLD}{RED}{msg}{RESET}")
        else:
            if stderr:
                label = self.get_translation("label_gui_error", "GUI Error:")
                print(f"{BOLD}{RED}{label}{RESET}\n{stderr}")
        return None

    def authenticate(self, username, password):
        from pyicloud import PyiCloudService
        msg_tmpl = self.get_translation("msg_authenticating", "Authenticating {id} ...")
        print(f"{BOLD}{BLUE}" + msg_tmpl.format(id=username) + f"{RESET}")
        
        try:
            api = PyiCloudService(username, password)
        except Exception as e:
            label = self.get_translation("err_authentication_failed", "Authentication failed:")
            print(f"{BOLD}{RED}{label}{RESET} {e}")
            return None

        if api.requires_2fa:
            msg = self.get_translation("label_2fa_required", "Two-factor authentication (2FA) required.")
            print(f"{BOLD}{YELLOW}{msg}{RESET}")
            prompt = self.get_translation("msg_enter_2fa_code", "Please enter the 6-digit verification code sent to your devices: ")
            code = input(prompt)
            if not code:
                msg = self.get_translation("err_no_code_entered", "No code entered.")
                print(f"{BOLD}{RED}{msg}{RESET}")
                return None
            
            if not api.validate_2fa_code(code):
                msg = self.get_translation("err_invalid_code", "Invalid verification code.")
                print(f"{BOLD}{RED}{msg}{RESET}")
                return None
            msg = self.get_translation("label_2fa_successful", "2FA Successful!")
            print(f"{BOLD}{GREEN}{msg}{RESET}")
            
        elif api.requires_2sa:
            msg = self.get_translation("label_2sa_required", "Two-step authentication (2SA) required.")
            print(f"{BOLD}{YELLOW}{msg}{RESET}")
            devices = api.trusted_devices
            for i, device in enumerate(devices):
                dev_name = device.get('deviceName', self.get_translation("label_unknown_device", "Unknown Device"))
                print(f"  {i}: {dev_name}")
            
            prompt = self.get_translation("msg_select_device", "Select device (0-{max}, default 0): ").format(max=len(devices)-1)
            choice = input(prompt) or "0"
            try:
                device = devices[int(choice)]
            except:
                device = devices[0]
                
            if not api.send_verification_code(device):
                msg = self.get_translation("err_failed_send_code", "Failed to send verification code.")
                print(f"{BOLD}{RED}{msg}{RESET}")
                return None
            
            prompt = self.get_translation("msg_enter_verification_code", "Please enter the verification code: ")
            code = input(prompt)
            if not api.validate_verification_code(device, code):
                msg = self.get_translation("err_verification_failed", "Verification failed.")
                print(f"{BOLD}{RED}{msg}{RESET}")
                return None
            msg = self.get_translation("label_2sa_successful", "2SA Successful!")
            print(f"{BOLD}{GREEN}{msg}{RESET}")

        return api

def main():
    tool = ICloudTool()
    
    parser = argparse.ArgumentParser(description="iCloud Tool", add_help=False)
    parser.add_argument("--login", action="store_true", help="Log in to iCloud and save session")
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    
    # Handle standard tool commands (setup, etc.)
    if tool.handle_command_line(parser): return
    
    args, unknown = parser.parse_known_args()
    
    if args.demo:
        # Template demo logic
        print(f"{BOLD}{BLUE}iCloud Tool Demo{RESET}")
        return

    if args.login:
        # 1. Run Login GUI
        msg = tool.get_translation("msg_opening_login_gui", "Opening login GUI...")
        print(f"{BOLD}{BLUE}{msg}{RESET}")
        credentials = tool.run_login_gui()
        
        if not credentials:
            sys.exit(1)
            
        # 2. Authenticate
        api = tool.authenticate(credentials["apple_id"], credentials["password"])
        
        if not api:
            sys.exit(1)
            
        # 3. Output metadata
        msg = tool.get_translation("msg_logged_in_successfully", "Successfully logged in!")
        print(f"\n{BOLD}{GREEN}{msg}{RESET}")
        label = tool.get_translation("label_account", "Account:")
        print(f"{BOLD}{label}{RESET} {credentials['apple_id']}")
        
        try:
            msg = tool.get_translation("msg_fetching_photos_meta", "Fetching photos metadata...")
            print(f"{BOLD}{BLUE}{msg}{RESET}")
            photos = api.photos.all
            try:
                count = len(photos)
                label = tool.get_translation("label_photos_count", "Photos Count:")
                print(f"{BOLD}{label}{RESET} {count}")
            except:
                label = tool.get_translation("label_photos_access_granted", "Photos: Access granted.")
                print(f"{BOLD}{label}{RESET}")
        except Exception as e:
            warning_label = tool.get_translation("label_warning", "Warning")
            err_msg = tool.get_translation("err_fetch_photo_meta", "Could not fetch photo metadata:")
            print(f"{BOLD}{YELLOW}{warning_label}:{RESET} {err_msg} {e}")
        return

    parser.print_help()

if __name__ == "__main__":
    main()
