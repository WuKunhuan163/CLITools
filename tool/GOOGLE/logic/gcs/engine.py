import json
import time
import uuid
import hashlib
import subprocess
import sys
from pathlib import Path

class GCSRemoteShell:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.data_dir = self.project_root / "tool" / "GOOGLE" / "data" / "gcs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.shells_file = self.data_dir / "shells.json"
        self.load_shells()

    def load_shells(self):
        if self.shells_file.exists():
            try:
                with open(self.shells_file, 'r', encoding='utf-8') as f:
                    self.shells_data = json.load(f)
            except:
                self.shells_data = {"shells": {}, "active_shell": None}
        else:
            self.shells_data = {"shells": {}, "active_shell": None}

    def save_shells(self):
        with open(self.shells_file, 'w', encoding='utf-8') as f:
            json.dump(self.shells_data, f, indent=2, ensure_ascii=False)

    def generate_id(self):
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:12]

    def create_shell(self, name=None):
        shell_id = self.generate_id()
        name = name or f"gcs_{shell_id}"
        config = {
            "id": shell_id,
            "name": name,
            "current_path": "/content",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_accessed": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.shells_data["shells"][shell_id] = config
        self.shells_data["active_shell"] = shell_id
        self.save_shells()
        print(f"Created new GCS shell: {name} (ID: {shell_id})")
        return shell_id

    def list_shells(self):
        if not self.shells_data["shells"]:
            print("No remote GCS shells found.")
            return
        print(f"GCS Shells ({len(self.shells_data['shells'])}):")
        for sid, cfg in self.shells_data["shells"].items():
            active = "*" if sid == self.shells_data["active_shell"] else " "
            print(f"{active} {cfg['name']} (ID: {sid}) - Path: {cfg['current_path']}")

    def get_active_shell(self):
        sid = self.shells_data.get("active_shell")
        if sid and sid in self.shells_data["shells"]:
            return self.shells_data["shells"][sid]
        return None

    def execute(self, cmd):
        shell = self.get_active_shell()
        if not shell:
            print("No active shell. Creating one...")
            self.create_shell()
            shell = self.get_active_shell()

        # Wrap command for Colab
        # We use a pattern similar to the original GDS
        remote_code = self.wrap_command(cmd, shell)
        
        print("\n" + "="*40)
        print("COPY AND RUN THIS IN GOOGLE COLAB:")
        print("="*40)
        print(remote_code)
        print("="*40 + "\n")

        # Call USERINPUT to get the result
        feedback = self.get_user_feedback(cmd)
        
        # Process and display feedback
        self.process_feedback(feedback, shell)

    def wrap_command(self, cmd, shell):
        # Very simple wrapper for now: cd to path and run cmd
        # We can enhance this later with output redirection etc.
        cwd = shell.get("current_path", "/content")
        
        # Colab-friendly bash block
        code = f"""
%%bash
cd "{cwd}"
{cmd}
# GCS_PWD_MARKER
pwd
"""
        return code.strip()

    def get_user_feedback(self, cmd):
        # Construct path to bin/USERINPUT or similar
        userinput_bin = self.project_root / "bin" / "USERINPUT"
        if not userinput_bin.exists():
            # Fallback to direct python call if bin not ready
            userinput_bin = self.project_root / "tool" / "USERINPUT" / "main.py"

        # Use the same python as currently running
        python_exec = sys.executable
        
        prompt_id = f"GCS: {cmd[:30]}..."
        try:
            res = subprocess.run(
                [str(python_exec), str(userinput_bin), "--id", prompt_id, "--timeout", "300"],
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                return res.stdout.strip()
            else:
                return f"Error: USERINPUT failed ({res.stderr})"
        except Exception as e:
            return f"Error: Failed to call USERINPUT ({e})"

    def process_feedback(self, feedback, shell):
        if not feedback:
            print("No result received.")
            return

        # Simple output processing
        # Try to extract the last line as the new path (based on GCS_PWD_MARKER logic)
        lines = feedback.splitlines()
        if lines:
            new_path = lines[-1].strip()
            if new_path.startswith("/") and "/" in new_path:
                shell["current_path"] = new_path
                shell["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
                self.save_shells()
                # Remove the path from output for display
                output = "\n".join(lines[:-1])
            else:
                output = feedback
        else:
            output = feedback

        print("\n--- GCS Remote Output ---")
        print(output)
        print("-------------------------\n")

    def enter_interactive(self):
        shell = self.get_active_shell()
        if not shell:
            self.create_shell()
            shell = self.get_active_shell()

        print(f"Entering GCS Interactive Mode (Shell: {shell['name']})")
        print("Type 'exit' or 'quit' to return to local shell.")
        
        while True:
            try:
                path = shell.get("current_path", "~")
                prompt = f"GCS:{path}$ "
                user_cmd = input(prompt).strip()
                
                if not user_cmd:
                    continue
                if user_cmd.lower() in ["exit", "quit"]:
                    break
                
                self.execute(user_cmd)
                # Refresh shell state after each command
                shell = self.get_active_shell()
                
            except (KeyboardInterrupt, EOFError):
                print("\nExiting interactive mode.")
                break

