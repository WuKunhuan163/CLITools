import sys
import os
import pickle
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
    sys.path.insert(0, str(project_root))

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException

def test_session_persistence(apple_id, password=None):
    cookie_file = Path(f"session_{apple_id}.pkl")
    
    # 1. Try to load existing session
    if cookie_file.exists():
        print(f"Found existing session cookies for {apple_id}. Attempting passwordless login...")
        try:
            # Initialize without password
            api = PyiCloudService(apple_id, "")
            
            # Load cookies
            with open(cookie_file, 'rb') as f:
                api.session.cookies.update(pickle.load(f))
            
            # Verify if session is still valid by calling a simple endpoint
            # requires_2fa check or account info
            print(f"Checking session validity...")
            _ = api.account.devices
            print("Successfully authenticated using stored cookies (No password needed)!")
            return True
        except Exception as e:
            print(f"Session reuse failed: {e}")
            print("Removing expired/invalid cookies.")
            cookie_file.unlink()
    
    # 2. Perform full login if needed
    if password:
        print(f"Performing full authentication for {apple_id}...")
        try:
            api = PyiCloudService(apple_id, password)
            
            if api.requires_2fa:
                print("Two-factor authentication is required. Please use the main app to verify.")
                return False
            
            # Save cookies for next time
            with open(cookie_file, 'wb') as f:
                pickle.dump(api.session.cookies, f)
            print(f"Successfully authenticated and saved session to {cookie_file}")
            return True
        except PyiCloudFailedLoginException:
            print("Authentication failed: Invalid credentials.")
        except Exception as e:
            print(f"Unexpected error: {e}")
    else:
        print("No password provided and no valid session found.")
    
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apple-id", required=True)
    parser.add_argument("--password", help="Password for initial login (if no session exists)")
    args = parser.parse_args()
    
    test_session_persistence(args.apple_id, args.password)

