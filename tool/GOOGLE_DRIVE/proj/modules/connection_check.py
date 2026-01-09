#!/usr/bin/env python3
"""
Connection Check - Remote Result File Verification Template

This module provides Connection Check, which is a code snippet connection checkhat can be injected
into remote commands to proactively verify result file access and detect shell crashes.

Key Features:
- Verifies access to expected result files using Google Drive API
- Implements retry mechanism with configurable attempts and intervals
- Auto-exits remote shell if verification fails
- Includes clipboard reminder during countdown
- Supports placeholder substitution for result filenames
- Uses cached ~/tmp folder ID for efficient verification
"""

import json
import os
from typing import Optional


class ConnectionCheck:
    """Connection Check generator for remote result file verification"""
    
    def __init__(self, main_instance=None):
        """
        Initialize Connection Check generator
        
        Args:
            main_instance: Reference to GoogleDriveShell instance
        """
        self.main_instance = main_instance
        
    def generate_template(self, result_filename: str, tmp_folder_id: Optional[str] = None, 
                         max_attempts: int = 20, interval_seconds: int = 1, command_hash: Optional[str] = None) -> str:
        """
        Generate Connection Check code snippet for remote execution
        
        Args:
            result_filename (str): Expected result filename (placeholder will be replaced)
            tmp_folder_id (str, optional): Cached ~/tmp folder ID. If None, will try to resolve
            max_attempts (int): Maximum retry attempts
            interval_seconds (int): Interval between attempts in seconds
            command_hash (str, optional): Command hash to display after successful verification
            
        Returns:
            str: Generated Connection Check code snippet
        """
        # Get tmp folder ID from cache if not provided
        if not tmp_folder_id:
            tmp_folder_id = self._get_cached_tmp_id()
        
        if not tmp_folder_id:
            return ""
        
        template = self._generate_verification_template(
            result_filename=result_filename,
            tmp_folder_id=tmp_folder_id,
            max_attempts=max_attempts,
            interval_seconds=interval_seconds,
            command_hash=command_hash
        )
        
        return template
    
    def _get_cached_tmp_id(self) -> Optional[str]:
        """Get cached ~/tmp folder ID from configuration"""
        try:
            from .path_constants import PathConstants
            path_constants = PathConstants()
            config_path = str(path_constants.GDS_PATH_IDS_FILE)
            
            if not os.path.exists(config_path):
                return None
                
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            return config.get("path_ids", {}).get("~/tmp")
        except Exception:
            return None
    
    def _generate_verification_template(self, result_filename: str, tmp_folder_id: str,
                                      max_attempts: int, interval_seconds: int, command_hash: Optional[str] = None) -> str:
        """Generate the actual verification template code"""
        
        # Get service account credentials for the template
        credentials_code = self._get_credentials_injection_code()
        template = '''
# Connection Check: Remote Result File Verification
# This code verifies result file access and detects shell crashes

# Create verification script
cat > /tmp/connection_check_verify.py << 'CONNECTION_CHECK_EOF'
#!/usr/bin/env python3

import os
import sys
import time
import json
import subprocess
os.system('clear')

def get_service_account_credentials():
    """Get service account credentials for Google Drive API"""
    try:
{credentials_code}
    except Exception as e:
        print(f"Failed to get credentials: {{e}}")
        return None

def verify_result_file_access(tmp_folder_id, result_filename, max_attempts, interval):
    """Verify access to result file using Google Drive API"""
    try:
        # Import Google API client
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        # Get credentials
        creds_dict = get_service_account_credentials()
        if not creds_dict:
            print("No credentials available, skipping verification")
            return True  # Graceful degradation - assume success if no credentials
        
        # Build service
        try:
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Failed to build service: {{e}}")
            return True  # Graceful degradation
        
        print(f"Starting verification for result file: {{result_filename}}")
        print(f"Using tmp folder ID: {{tmp_folder_id}}")
        print(f"Max attempts: {{max_attempts}}, Interval: {{interval}}s")
        
        print ("Verifying .", end = "", flush = True)
        for attempt in range(1, max_attempts + 1):
            try:
                print (".", end = "", flush = True)
                
                # List files in tmp folder to check if result file exists
                results = service.files().list(
                    q=f"'{{tmp_folder_id}}' in parents and name='{{result_filename}}'",
                    fields="files(id, name, createdTime)"
                ).execute()
                
                files = results.get('files', [])
                if files:
                    print(f"Result file found: {{result_filename}}")
                    return True
                else:
                    pass
                
            except Exception as e:
                pass
            
            if attempt < max_attempts:
                time.sleep(interval)
        
        print(f"Failed to access result file after {{max_attempts}} attempts")
        return False
        
    except ImportError:
        print("Google API client not available, skipping verification")
        return True  # Graceful degradation
    except Exception as e:
        print(f"Verification failed: {{e}}")
        return False

def show_clipboard_reminder():
    """Show clipboard reminder during countdown"""
    print("📋REMINDER: The command is still in your clipboard!")
    print("You can run the above GOOGLE_DRIVE --remount cell and paste it to the terminal again")
    print("Or you may provide feedback in direct mode without re-running the cell")

def main():
    """Main verification function"""
    result_filename = "{result_filename}"
    tmp_folder_id = "{tmp_folder_id}"
    max_attempts = {max_attempts}
    interval = {interval_seconds}

    print("Remote Shell Connection Check")
    
    # Verify result file access
    success = verify_result_file_access(tmp_folder_id, result_filename, max_attempts, interval)
    
    if not success:
        print("🚨SHELL CRASH DETECTED: Cannot access result file. ")
        print("Current session may have disconnected and cannot be used anymore. ")
        
        # Show clipboard reminder
        show_clipboard_reminder()
        
        # Countdown before exit
        print("Initiating emergency shutdown in 5 seconds...")   
        for i in range(5, 0, -1):
            print(f"Shutdown in {{i}} seconds... (Ctrl+C to cancel)")
            time.sleep(1)
        
        print("💥Emergency shutdown: Clearing remote runtime")
        try:
            from google.colab import runtime
            runtime.unassign()
        except:
            # Fallback to sys.exit if runtime.unassign() fails
            sys.exit(1)
    else:
        print("Result file access verified. Remote connection is healthy")
        os.system("clear")
        print("✅执行完成")
        # Display command hash if provided
        command_hash = "{command_hash}"
        if command_hash and command_hash != "{{command_hash}}":
            print(f"Command hash: {{command_hash.upper()}}")

if __name__ == "__main__":
    main()
CONNECTION_CHECK_EOF

# Execute verification script
python3 /tmp/connection_check_verify.py

# Clean up verification script
rm -f /tmp/connection_check_verify.py
'''
        
        # Format the template with all parameters
        try:
            formatted_template = template.format(
                credentials_code=credentials_code,
                result_filename=result_filename,
                tmp_folder_id=tmp_folder_id,
                max_attempts=max_attempts,
                interval_seconds=interval_seconds,
                command_hash=command_hash or "None"
            )
            return formatted_template.strip()
        except Exception as e:
            raise
    
    def _get_credentials_injection_code(self) -> str:
        """Generate code to inject service account credentials into the template"""
        try:
            # Try to get credentials from local environment first
            credentials_dict = self._get_local_credentials()
            
            if credentials_dict:
                credentials_json = json.dumps(credentials_dict)
                return f'''
        # Injected credentials from local environment
        import json
        creds_dict = {credentials_json}
        return creds_dict'''
            else:
                credentials_env_vars = [
                    'GOOGLE_APPLICATION_CREDENTIALS_JSON',
                    'GOOGLE_SERVICE_ACCOUNT_JSON',
                    'GDS_SERVICE_ACCOUNT_JSON'
                ]
                
                # Generate code to check environment variables
                env_check_code = []
                for env_var in credentials_env_vars:
                    env_check_code.append(f'''
        # Try {env_var}
        creds_json = os.environ.get('{env_var}')
        if creds_json:
            try:
                return json.loads(creds_json)
            except:
                pass''')
                
                return ''.join(env_check_code) + '''
        
        # If no environment credentials, return None
        return None'''
            
        except Exception as e:
            return "        return None  # Credentials injection failed"
    
    def _get_local_credentials(self):
        """Get credentials from GoogleDriveService instance or environment variables"""
        try:
            # Method 1: Get credentials from main_instance.drive_service (primary method)
            if self.main_instance and hasattr(self.main_instance, 'drive_service'):
                drive_service = self.main_instance.drive_service
                
                # Check if drive_service has key_data (from environment variables)
                if hasattr(drive_service, 'key_data') and drive_service.key_data:
                    return drive_service.key_data
                
                # Check if drive_service has credentials object
                if hasattr(drive_service, 'credentials') and drive_service.credentials:
                    credentials = drive_service.credentials
                    if hasattr(credentials, '_service_account_info'):
                        return credentials._service_account_info
                    elif hasattr(credentials, 'service_account_email'):
                        return self._reconstruct_credentials_from_env()
            
            # Method 2: Try to reconstruct from individual environment variables
            reconstructed = self._reconstruct_credentials_from_env()
            if reconstructed:
                return reconstructed
            
            # Method 3: Check JSON-format environment variables (fallback)
            credentials_env_vars = [
                'GOOGLE_APPLICATION_CREDENTIALS_JSON',
                'GOOGLE_SERVICE_ACCOUNT_JSON',
                'GDS_SERVICE_ACCOUNT_JSON'
            ]
            
            for env_var in credentials_env_vars:
                creds_json = os.environ.get(env_var)
                if creds_json:
                    try:
                        return json.loads(creds_json)
                    except Exception as e:
                        continue
            
            # Method 4: Check GOOGLE_APPLICATION_CREDENTIALS file
            creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_file and os.path.exists(creds_file):
                try:
                    with open(creds_file, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    pass
            return None
            
        except Exception as e:
            return None
    
    def _reconstruct_credentials_from_env(self):
        """Reconstruct credentials dict from individual environment variables"""
        try:
            # These are the environment variables used by GoogleDriveService
            required_env_vars = {
                'type': 'GOOGLE_DRIVE_SERVICE_TYPE',
                'project_id': 'GOOGLE_DRIVE_PROJECT_ID',
                'private_key_id': 'GOOGLE_DRIVE_PRIVATE_KEY_ID',
                'private_key': 'GOOGLE_DRIVE_PRIVATE_KEY',
                'client_email': 'GOOGLE_DRIVE_CLIENT_EMAIL',
                'client_id': 'GOOGLE_DRIVE_CLIENT_ID',
                'auth_uri': 'GOOGLE_DRIVE_AUTH_URI',
                'token_uri': 'GOOGLE_DRIVE_TOKEN_URI',
                'auth_provider_x509_cert_url': 'GOOGLE_DRIVE_AUTH_PROVIDER_CERT_URL',
                'client_x509_cert_url': 'GOOGLE_DRIVE_CLIENT_CERT_URL'
            }
            
            # Build credentials dict
            key_data = {}
            missing_vars = []
            
            for json_key, env_var in required_env_vars.items():
                value = os.environ.get(env_var)
                if value is None:
                    missing_vars.append(env_var)
                else:
                    key_data[json_key] = value
            
            # Check optional field
            universe_domain = os.environ.get('GOOGLE_DRIVE_UNIVERSE_DOMAIN')
            if universe_domain:
                key_data['universe_domain'] = universe_domain
            
            # If missing required variables, return None
            if missing_vars:
                return None
            
            return key_data
            
        except Exception as e:
            return None


def create_connection_check_instance(main_instance=None) -> ConnectionCheck:
    """
    Factory function to create Connection Check instance
    
    Args:
        main_instance: Reference to GoogleDriveShell instance
        
    Returns:
        ConnectionCheck: Configured Connection Check instance
    """
    return ConnectionCheck(main_instance=main_instance)
