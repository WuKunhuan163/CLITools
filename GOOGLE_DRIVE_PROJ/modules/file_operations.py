
from .file_core import FileCore
from .text_operations import TextOperations
from .commands.upload_command import UploadCommand

class FileOperations:
    """
    Main file operations coordinator - delegates to specialized modules
    """
    
    def __init__(self, drive_service, main_instance=None):
        """Initialize all specialized modules"""
        self.drive_service = drive_service
        self.main_instance = main_instance
        self.file_core = FileCore(drive_service, main_instance)
        self.text_operations = TextOperations(drive_service, main_instance)
        self.upload_cmd = UploadCommand(main_instance)

    # These methods have been moved to their respective command classes
    # and are now accessed through the command_registry
    def cmd_venv(self, *args, **kwargs):
        """Delegate to VenvCommand through command_registry"""
        command = self.main_instance.command_registry.get_command('venv')
        if command:
            return command.cmd_venv(*args, **kwargs)
        else:
            return {"success": False, "error": "VenvCommand not found"}
    
    def cmd_pyenv(self, *args, **kwargs):
        """Delegate to PyenvCommand through command_registry"""
        command = self.main_instance.command_registry.get_command('pyenv')
        if command:
            return command.cmd_pyenv(*args, **kwargs)
        else:
            return {"success": False, "error": "PyenvCommand not found"}
    
    def cmd_pip(self, *args, **kwargs):
        """Delegate to PipCommand through command_registry"""
        command = self.main_instance.command_registry.get_command('pip')
        if command:
            return command.cmd_pip(*args, **kwargs)
        else:
            return {"success": False, "error": "PipCommand not found"}
    
    def cmd_deps(self, *args, **kwargs):
        """Delegate to DepsCommand through command_registry"""
        command = self.main_instance.command_registry.get_command('deps')
        if command:
            return command.cmd_deps(*args, **kwargs)
        else:
            return {"success": False, "error": "DepsCommand not found"}
    
    def cmd_python(self, *args, **kwargs):
        """Delegate to PythonCommand through command_registry"""
        command = self.main_instance.command_registry.get_command('python')
        return command.cmd_python(*args, **kwargs)
    
    def cmd_upload_folder(self, *args, **kwargs):
        """Delegate to upload_command"""
        return self.upload_cmd.cmd_upload_folder(*args, **kwargs)
    
    def cmd_upload(self, *args, **kwargs):
        """Delegate to upload_command"""
        return self.upload_cmd.cmd_upload(*args, **kwargs)
    
    def cmd_download(self, *args, **kwargs):
        """Delegate to download command (через command_registry или file_core если еще существует)"""
        # Проверяем, есть ли метод в file_core
        if hasattr(self.file_core, 'cmd_download'):
            return self.file_core.cmd_download(*args, **kwargs)
        else:
            # Если нет, используем command_registry
            command = self.main_instance.command_registry.get_command('download')
            if command:
                return command.execute('download', list(args), **kwargs)
            else:
                return {"success": False, "error": "Download command not found"}
    
    def cmd_pwd(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_pwd(*args, **kwargs)
    
    def cmd_ls(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_ls(*args, **kwargs)
    
    def cmd_cd(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_cd(*args, **kwargs)
    
    def cmd_touch(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_touch(*args, **kwargs)
    
    def cmd_rm(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_rm(*args, **kwargs)
    
    def cmd_cp(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_cp(*args, **kwargs)
    
    def cmd_mv(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_mv(*args, **kwargs)
    
    def wait_for_file_sync(self, *args, **kwargs):
        """Delegate to upload_command"""
        return self.upload_cmd.wait_for_file_sync(*args, **kwargs)
    
    def cmd_edit(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_edit(*args, **kwargs)
    
    def _create_text_file(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations._create_text_file(*args, **kwargs)
    
    def cmd_nano(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_nano(*args, **kwargs)
    
    def cmd_vim(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_vim(*args, **kwargs)
    
    def cmd_cat(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_cat(*args, **kwargs)
    
    def cmd_head(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_head(*args, **kwargs)
    
    def cmd_tail(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_tail(*args, **kwargs)
    
    def cmd_grep(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_grep(*args, **kwargs)
    
    def cmd_find(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_find(*args, **kwargs)
    
    def cmd_wc(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_wc(*args, **kwargs)
    
    def cmd_read(self, filename, *args, **kwargs):
        """Read file content - delegate to text_operations cat command for now"""
        # For now, use cat command as a simple implementation of read
        return self.text_operations.cmd_cat(filename)
    
    def cmd_linter(self, filename, *args, **kwargs):
        """Lint file - delegate to linter functionality"""
        try:
            # Get file content first
            cat_result = self.text_operations.cmd_cat(filename)
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"Could not read file {filename}: {cat_result.get('error', 'Unknown error')}"
                }
            
            content = cat_result.get("output", "")
            
            # Import and use the new LINTER tool
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from LINTER import MultiLanguageLinter
            linter = MultiLanguageLinter()
            
            # Run linter on content
            result = linter.lint_content(content, filename)
            
            # Format output for display
            output_lines = []
            output_lines.append(f"Language: {result.get('language', 'unknown')}")
            output_lines.append(f"Status: {'PASS' if result.get('success', False) else 'FAIL'}")
            output_lines.append(f"Message: {result.get('message', '')}")
            
            if result.get('errors'):
                output_lines.append("\nErrors:")
                for error in result['errors']:
                    output_lines.append(f"  • {error}")
            
            if result.get('warnings'):
                output_lines.append("\nWarnings:")
                for warning in result['warnings']:
                    output_lines.append(f"  • {warning}")
            
            if result.get('info'):
                output_lines.append("\nInfo:")
                for info in result['info']:
                    output_lines.append(f"  • {info}")
            
            return {
                "success": True,
                "output": "\n".join(output_lines),
                "has_errors": bool(result.get('errors')),
                "linter_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Linter execution failed: {str(e)}"
            }
    
    def check_network_connection(self):
        """Check network connection"""
        try:
            import urllib.request
            urllib.request.urlopen('http://www.google.com', timeout=1)
            return True
        except:
            return False
    
    def ensure_google_drive_desktop_running(self):
        """Ensure Google Drive Desktop is running"""
        try:
            import subprocess
            import platform
            import time
            
            # Check if running
            result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and bool(result.stdout.strip()):
                return True
            
            if platform.system() == "Darwin":
                subprocess.run(['open', '-a', 'Google Drive'], check=False)
            elif platform.system() == "Linux":
                subprocess.run(['google-drive'], check=False)
            elif platform.system() == "Windows":
                subprocess.run(['start', 'GoogleDrive'], shell=True, check=False)
            
            # Wait for startup
            for i in range(10):
                time.sleep(1)
                result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and bool(result.stdout.strip()):
                    print(f"Google Drive Desktop started successfully")
                    return True
            
            print(f"Could not confirm Google Drive Desktop startup")
            return False
            
        except Exception as e:
            print(f"Error: Error managing Google Drive Desktop: {e}")
            return False
