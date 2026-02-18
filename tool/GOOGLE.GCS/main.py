#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
def find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root:
    root_str = str(project_root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
    
    # Remove script dir from path to avoid shadowing
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir in sys.path:
        sys.path.remove(script_dir)
    
    # print(f"DEBUG FINAL sys.path: {sys.path}")
else:
    # Fallback
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color

def main():
    # GCS is a subtool of GOOGLE, using the flat namespace naming convention.
    tool = ToolBase("GOOGLE.GCS")
    
    parser = argparse.ArgumentParser(description="Google Drive Remote Controller (GCS)", add_help=False)
    parser.add_argument("command", nargs="?", choices=["ls", "cat", "setup-tutorial"], help="Subcommand to run")
    parser.add_argument("--folder-id", help="Target Google Drive folder ID")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    if args.command == "setup-tutorial":
        # Since GOOGLE.GCS contains a dot, we use importlib to load it properly
        import importlib.util
        tutorial_path = Path(__file__).resolve().parent / "logic" / "tutorial" / "setup_guide" / "main.py"
        spec = importlib.util.spec_from_file_location("google_gcs_tutorial", str(tutorial_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        res = module.run_setup_tutorial()
        if res.get("status") == "success":
            print(f"{get_color('BOLD')}{get_color('GREEN')}Successfully{get_color('RESET')} completed GCS setup tutorial.")
        else:
            print(f"{get_color('BOLD')}{get_color('RED')}Tutorial exited{get_color('RESET')}: {res.get('reason', 'Unknown')}")
        return

    if args.command in ["ls", "cat"]:
        # We need credentials to perform these actions
        key_path = project_root / "tmp" / "console-control-466711-41aae5bfae1a.json" # Default for now
        if not key_path.exists():
            print(f"{get_color('BOLD')}{get_color('RED')}Error{get_color('RESET')}: Credentials not found at {key_path}")
            return

        folder_id = args.folder_id or "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f" # Default for now
        
        # Helper to get access token
        def get_access_token(info):
            import jwt
            import requests
            import time
            now = int(time.time())
            payload = {
                "iss": info["client_email"],
                "scope": "https://www.googleapis.com/auth/drive.readonly",
                "aud": info["token_uri"],
                "exp": now + 3600,
                "iat": now
            }
            token = jwt.encode(payload, info["private_key"], algorithm="RS256")
            res = requests.post(info["token_uri"], data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": token
            }, timeout=10)
            if res.status_code != 200:
                raise Exception(f"Auth Error: {res.text}")
            return res.json()["access_token"]

        import json
        import requests
        with open(key_path, 'r') as f:
            info = json.load(f)
            
        try:
            token = get_access_token(info)
            headers = {"Authorization": f"Bearer {token}"}
            
            if args.command == "ls":
                params = {
                    "q": f"'{folder_id}' in parents and trashed = false",
                    "fields": "files(id, name, mimeType)"
                }
                res = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=10)
                if res.status_code == 200:
                    files = res.json().get("files", [])
                    print(f"\n{get_color('BOLD')}Contents of folder {folder_id}:{get_color('RESET')}")
                    for f in files:
                        print(f"- {f['name']} ({f['id']}) [{f['mimeType']}]")
                else:
                    print(f"API Error: {res.text}")
            
            elif args.command == "cat":
                file_id = args.args[0] if args.args else None
                if not file_id:
                    print("Usage: GOOGLE.GCS cat <FILE_ID>")
                    return
                
                # Download file content
                res = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers, timeout=15)
                if res.status_code == 200:
                    print(res.text)
                else:
                    print(f"API Error: {res.text}")
                    
        except Exception as e:
            print(f"{get_color('BOLD')}{get_color('RED')}Error{get_color('RESET')}: {e}")
        return

    print(f"GCS executing command: {args.command}")

if __name__ == "__main__":
    main()
