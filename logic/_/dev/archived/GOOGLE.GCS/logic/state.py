import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

class GCSStateManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.data_dir = project_root / "tool" / "GOOGLE.GCS" / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "shell_state.json"
        self.state = self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        
        # Initial state with default shell
        default_id = self._generate_id()
        return {
            "active_shell_id": default_id,
            "shells": {
                default_id: {
                    "name": "default",
                    "remote_cwd": "/content",
                    "venv_name": "base",
                    "shell_type": "bash",
                    "created_at": datetime.now().isoformat(),
                    "last_used": datetime.now().isoformat()
                }
            }
        }

    def _generate_id(self):
        import random
        ts = str(int(time.time()))
        salt = str(random.randint(0, 999999))
        h = hashlib.md5(f"{ts}_{salt}".encode()).hexdigest()[:6]
        return f"{ts}_{h}"

    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_active_shell_id(self):
        return self.state["active_shell_id"]

    def get_shell_info(self, shell_id=None):
        shell_id = shell_id or self.get_active_shell_id()
        return self.state["shells"].get(shell_id)

    def create_shell(self, name: str, shell_type: str = "bash"):
        shell_id = self._generate_id()
        self.state["shells"][shell_id] = {
            "name": name,
            "remote_cwd": "/content",
            "venv_name": "base",
            "shell_type": shell_type,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }
        self.state["active_shell_id"] = shell_id
        self._save_state()
        return shell_id

    def switch_shell(self, shell_id: str):
        if shell_id in self.state["shells"]:
            self.state["active_shell_id"] = shell_id
            self.state["shells"][shell_id]["last_used"] = datetime.now().isoformat()
            self._save_state()
            return True
        return False

    def list_shells(self):
        # Return list of (id, name, last_used)
        return [(sid, sinfo["name"], sinfo["last_used"]) for sid, sinfo in self.state["shells"].items()]

    def update_shell(self, shell_id: str, **kwargs):
        if shell_id in self.state["shells"]:
            self.state["shells"][shell_id].update(kwargs)
            self.state["shells"][shell_id]["last_used"] = datetime.now().isoformat()
            self._save_state()


