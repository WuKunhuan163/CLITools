import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from typing import Dict

class VpnEngine:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.tool_dir = self.project_root / "tool" / "VPN"
        self.data_dir = self.tool_dir / "data"
        self.bin_dir = self.data_dir / "bin"
        self.pid_file = self.data_dir / "gost.pid"
        self.config_file = self.data_dir / "config.json"
        
        # Default settings
        self.default_port = 8080
        self.gost_version = "2.11.5"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)

    def get_gost_bin(self) -> Path:
        """Returns the path to the GOST binary, downloading it if necessary."""
        system = sys.platform
        arch = "amd64" 
        if os.uname().machine == "arm64":
            arch = "arm64"
            
        bin_name = f"gost-{system}-{arch}"
        if system == "darwin":
            bin_name = f"gost-darwin-{arch}"
        elif system == "win32":
            bin_name = f"gost-windows-{arch}.exe"
        else:
            bin_name = f"gost-linux-{arch}"
            
        target_path = self.bin_dir / bin_name
        
        if not target_path.exists():
            # Check if we have it in tmp from previous exploration
            tmp_gost = self.project_root / "tmp" / "gost"
            if tmp_gost.exists():
                import shutil
                shutil.copy(tmp_gost, target_path)
                target_path.chmod(target_path.stat().st_mode | 0o111)
            else:
                # Need to download
                # url = f"https://github.com/ginuerzh/gost/releases/download/v{self.gost_version}/{bin_name}.gz"
                pass
                
        return target_path

    def start_proxy(self, port: int = None, forward: str = None) -> bool:
        """Starts the GOST proxy server."""
        if self.is_running():
            self.stop_proxy() # Restart to apply new settings
            
        port = port or self.default_port
        gost_bin = self.get_gost_bin()
        if not gost_bin.exists():
            print(f"Error: GOST binary not found at {gost_bin}")
            return False
            
        cmd = [str(gost_bin), "-L", f":{port}"]
        if forward:
            cmd.extend(["-F", forward])
        
        # Start in background
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setpgrp # Create new process group
            )
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait a bit to ensure it started
            time.sleep(1)
            return self.is_running()
        except Exception as e:
            print(f"Error starting proxy: {e}")
            return False

    def stop_proxy(self) -> bool:
        """Stops the GOST proxy server."""
        if not self.pid_file.exists():
            return True
            
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            if self.is_running():
                os.kill(pid, signal.SIGKILL)
                
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True
        except ProcessLookupError:
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True
        except Exception as e:
            print(f"Error stopping proxy: {e}")
            return False

    def is_running(self) -> bool:
        """Checks if the proxy server is running."""
        if not self.pid_file.exists():
            return False
            
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            import psutil
            return psutil.pid_exists(pid)
        except:
            return False

    def get_proxy_urls(self) -> Dict[str, str]:
        """Returns proxy URLs if running."""
        if not self.is_running():
            return {}
            
        port = self.default_port
        url = f"http://127.0.0.1:{port}"
        return {
            "http": url,
            "https": url
        }
