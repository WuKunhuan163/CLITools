#!/usr/bin/env python3
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
            "--title", "iCloud Login",
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
            print(f"{BOLD}{YELLOW}Login cancelled by user.{RESET}")
        elif result and result.get("status") == "timeout":
            print(f"{BOLD}{RED}Login timed out.{RESET}")
        else:
            if stderr:
                print(f"{BOLD}{RED}GUI Error:{RESET}\n{stderr}")
        return None

    def authenticate(self, username, password):
        from pyicloud import PyiCloudService
        print(f"{BOLD}{BLUE}Authenticating{RESET} {username} ...")
        
        try:
            api = PyiCloudService(username, password)
        except Exception as e:
            print(f"{BOLD}{RED}Authentication failed:{RESET} {e}")
            return None

        if api.requires_2fa:
            print(f"{BOLD}{YELLOW}Two-factor authentication (2FA) required.{RESET}")
            code = input("Please enter the 6-digit verification code sent to your devices: ")
            if not code:
                print(f"{BOLD}{RED}No code entered.{RESET}")
                return None
            
            if not api.validate_2fa_code(code):
                print(f"{BOLD}{RED}Invalid verification code.{RESET}")
                return None
            print(f"{BOLD}{GREEN}2FA Successful!{RESET}")
            
        elif api.requires_2sa:
            print(f"{BOLD}{YELLOW}Two-step authentication (2SA) required.{RESET}")
            devices = api.trusted_devices
            for i, device in enumerate(devices):
                print(f"  {i}: {device.get('deviceName', 'Unknown Device')}")
            
            choice = input(f"Select device (0-{len(devices)-1}, default 0): ") or "0"
            try:
                device = devices[int(choice)]
            except:
                device = devices[0]
                
            if not api.send_verification_code(device):
                print(f"{BOLD}{RED}Failed to send verification code.{RESET}")
                return None
            
            code = input("Please enter the verification code: ")
            if not api.validate_verification_code(device, code):
                print(f"{BOLD}{RED}Verification failed.{RESET}")
                return None
            print(f"{BOLD}{GREEN}2SA Successful!{RESET}")

        return api

def main():
    tool = ICloudTool()
    
    parser = argparse.ArgumentParser(description="iCloud Tool", add_help=False)
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    
    # Handle standard tool commands (setup, etc.)
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    if args.demo:
        # Template demo logic
        print(f"{BOLD}{BLUE}iCloud Tool Demo{RESET}")
        return

    # 1. Run Login GUI
    print(f"{BOLD}{BLUE}Opening login GUI...{RESET}")
    credentials = tool.run_login_gui()
    
    if not credentials:
        sys.exit(1)
        
    # 2. Authenticate
    api = tool.authenticate(credentials["apple_id"], credentials["password"])
    
    if not api:
        sys.exit(1)
        
    # 3. Output metadata
    print(f"\n{BOLD}{GREEN}Successfully logged in!{RESET}")
    print(f"{BOLD}Account:{RESET} {credentials['apple_id']}")
    
    try:
        print(f"{BOLD}{BLUE}Fetching photos metadata...{RESET}")
        photos = api.photos.all
        try:
            count = len(photos)
            print(f"{BOLD}Photos Count:{RESET} {count}")
        except:
            print(f"{BOLD}Photos:{RESET} Access granted.")
            
        for photo in photos:
            print(f"\n{BOLD}Latest Photo Sample:{RESET}")
            print(f"  Filename: {photo.filename}")
            print(f"  Created:  {photo.created}")
            print(f"  Size:     {photo.size} bytes")
            break
            
    except Exception as e:
        print(f"{BOLD}{YELLOW}Warning:{RESET} Could not fetch photo metadata: {e}")

if __name__ == "__main__":
    main()
