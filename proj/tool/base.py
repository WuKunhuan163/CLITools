import os
import sys
import subprocess
from pathlib import Path
import json
import traceback
from datetime import datetime

class ToolBase:
    """Base class for all tools to handle dependencies, common utilities, and exception logging."""
    
    def __init__(self, tool_name):
        self.tool_name = tool_name
        self.script_dir = Path(sys.modules[self.__module__].__file__).resolve().parent
        self.project_root = self.script_dir.parent.parent
        self.tool_json_path = self.script_dir / "tool.json"
        self.dependencies = []
        self._load_metadata()

    def _load_metadata(self):
        if self.tool_json_path.exists():
            try:
                with open(self.tool_json_path, 'r') as f:
                    data = json.load(f)
                    self.dependencies = data.get("dependencies", [])
            except Exception:
                pass

    def check_dependencies(self):
        """Check if all required dependencies are installed and operational."""
        missing = []
        for dep in self.dependencies:
            dep_dir = self.project_root / "tool" / dep
            if not dep_dir.exists():
                missing.append(dep)
        
        if missing:
            from proj.config import get_color
            RED = get_color("RED", "\033[31m")
            BOLD = get_color("BOLD", "\033[1m")
            RESET = get_color("RESET", "\033[0m")
            
            print(f"{BOLD}{RED}Error{RESET}: Tool '{self.tool_name}' missing dependencies: {', '.join(missing)}")
            print(f"Please run: TOOL install {self.tool_name}")
            return False
        return True

    def get_tool_path(self, other_tool_name):
        """Get the directory path of another tool."""
        return self.project_root / "tool" / other_tool_name

    def call_other_tool(self, other_tool_name, args, capture_output=False):
        """Safely call another tool via its bin shortcut or main.py."""
        bin_path = self.project_root / "bin" / other_tool_name
        if not bin_path.exists():
            # Try main.py
            bin_path = self.project_root / "tool" / other_tool_name / "main.py"
            
        if not bin_path.exists():
            raise RuntimeError(f"Tool '{other_tool_name}' not found.")
            
        cmd = [str(bin_path)] + args
        return subprocess.run(cmd, capture_output=capture_output, text=True)

    def handle_command_line(self):
        """
        Process command line arguments. 
        If 'setup' is the first argument, run the tool's setup.py.
        Returns True if a command was handled and the tool should exit.
        """
        if len(sys.argv) > 1 and sys.argv[1] == "setup":
            self.run_setup()
            return True
        return False

    def run_setup(self):
        """Execute the tool's setup.py script using ProgressTuringMachine."""
        from proj.turing.models.progress import ProgressTuringMachine
        from proj.turing.core import TuringStage
        from proj.config import get_color
        
        setup_script = self.script_dir / "setup.py"
        if not setup_script.exists():
            RED = get_color("RED", "\033[31m")
            BOLD = get_color("BOLD", "\033[1m")
            RESET = get_color("RESET", "\033[0m")
            print(f"{BOLD}{RED}Error{RESET}: Tool '{self.tool_name}' does not have a setup.py script.")
            sys.exit(1)
        
        # Capture failure reason to display briefly
        failure_reason = [None]

        def run_setup_action():
            try:
                # Use current python to run setup.py
                # Pass --py-version if specified in sys.argv
                args = sys.argv[2:]
                res = subprocess.run([sys.executable, str(setup_script)] + args, capture_output=True, text=True)
                if res.returncode != 0:
                    # Brief reason: last non-empty line of stderr or stdout
                    reason = res.stderr.strip().split('\n')[-1] or res.stdout.strip().split('\n')[-1]
                    failure_reason[0] = reason
                    # Log full output as requested
                    self.handle_exception(RuntimeError(f"Setup failed for {self.tool_name}:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"))
                return res.returncode == 0
            except Exception as e:
                failure_reason[0] = str(e)
                self.handle_exception(e)
                return False

        tm = ProgressTuringMachine()
        # "Running setup" should be blue and bold. 
        # In ProgressTuringMachine, active_status is colored and bolded.
        tm.add_stage(TuringStage(
            name=self.get_translation("label_the_tool", "the {name} tool").format(name=self.tool_name),
            action=run_setup_action,
            active_status=self.get_translation("label_running_setup", "Running setup"),
            success_status=self.get_translation("label_successfully", "Successfully"),
            fail_status=self.get_translation("label_failed", "Failed"),
            success_name=self.get_translation("label_setup_success_name", "setup {name} tool").format(name=self.tool_name),
            fail_name=self.get_translation("label_setup_fail_name", "to setup the {name} tool").format(name=self.tool_name)
        ))
        
        if not tm.run():
            if failure_reason[0]:
                print(f"  Reason: {failure_reason[0]}")
            sys.exit(1)
        sys.exit(0)

    def handle_exception(self, e):
        """Unified exception handling and logging."""
        from proj.config import get_color
        from proj.audit.utils import AuditManager
        from proj.utils import cleanup_old_files
        
        RED = get_color("RED", "\033[31m")
        BOLD = get_color("BOLD", "\033[1m")
        RESET = get_color("RESET", "\033[0m")
        
        error_msg = f"{BOLD}{RED}Error{RESET}: {str(e)}"
        print(error_msg, file=sys.stderr, flush=True)
        
        # Save full traceback to exception log
        log_dir = self.project_root / "data" / "exception" / self.tool_name
        am = AuditManager(log_dir, component_name=f"{self.tool_name}_EXCEPTION")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "traceback": traceback.format_exc(),
            "command": " ".join(sys.argv)
        }
        am.save(f"exception_{timestamp}", log_data)
        
        # Limit logs to 50, deleting half when limit reached
        cleanup_old_files(log_dir, "*.json", limit=50)

    def get_translation(self, key, default):
        """Get tool-specific translation with fallback to root."""
        from proj.lang.utils import get_translation
        # 1. Try tool-specific project directory (e.g., tool/NAME/proj/)
        res = get_translation(str(self.script_dir / "proj"), key, None)
        if res and res != key: return res # Found in tool
        
        # 2. Try tool's core directory (e.g., tool/NAME/core/) - some tools use this
        res = get_translation(str(self.script_dir / "core"), key, None)
        if res and res != key: return res
        
        # 3. Fallback to root project translations (proj/translation/*.json)
        return get_translation(str(self.project_root / "proj"), key, default)

    def setup_gui(self):
        """Centralized GUI environment setup."""
        from proj.gui import setup_gui_environment
        setup_gui_environment()

