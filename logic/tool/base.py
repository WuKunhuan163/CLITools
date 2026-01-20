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
        
        # Ensure project root is in path for imports
        if str(self.project_root) not in sys.path:
            sys.path.append(str(self.project_root))
            
        self.tool_json_path = self.script_dir / "tool.json"
        self.dependencies = []
        self._load_metadata()
        
        # Auto-reexecute with correct python if PYTHON is a dependency
        if "PYTHON" in self.dependencies:
            from logic.utils import check_and_reexecute_with_python
            check_and_reexecute_with_python(self.tool_name)

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
            from logic.config import get_color
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
        from logic.turing.models.progress import ProgressTuringMachine
        from logic.turing.logic import TuringStage
        from logic.config import get_color
        
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
                    # Clear the "Running..." line before printing captured output
                    sys.stdout.write(f"\r\033[K")
                    sys.stdout.flush()
                    
                    # Brief reason: last non-empty line of stderr or stdout
                    reason = res.stderr.strip().split('\n')[-1] or res.stdout.strip().split('\n')[-1]
                    failure_reason[0] = reason
                    # Log full output but keep terminal output brief
                    self.handle_exception(RuntimeError(f"Setup failed for {self.tool_name}:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"), print_error=False)
                    # If it's a "Python not found" or similar logical error, 
                    # we might want to print the full captured stdout/stderr 
                    # so the user sees the detailed instructions from the tool itself.
                    if res.stdout: print(res.stdout)
                    if res.stderr: print(res.stderr)
                return res.returncode == 0
            except Exception as e:
                failure_reason[0] = str(e)
                self.handle_exception(e)
                return False

        tm = ProgressTuringMachine()
        # "Running setup" should be blue and bold. 
        # In ProgressTuringMachine, active_status is colored and bolded.
        tm.add_stage(TuringStage(
            name=self.get_translation("label_the_tool_setup", "for the {name} tool").format(name=self.tool_name),
            action=run_setup_action,
            active_status=self.get_translation("label_running_setup", "Running setup"),
            success_status=self.get_translation("label_successfully", "Successfully"),
            fail_status=self.get_translation("label_failed_to_setup", "Failed to setup"),
            success_name=self.get_translation("label_setup_success_name", "setup {name} tool").format(name=self.tool_name),
            fail_name=self.get_translation("label_the_tool_name", "the {name} tool").format(name=self.tool_name)
        ))
        
        if not tm.run(ephemeral=True):
            if failure_reason[0]:
                # Only print reason if it's not already in the captured output
                # (Heuristic: check if reason is in the captured output)
                pass
            sys.exit(1)
        sys.exit(0)

    def handle_exception(self, e, print_error=True):
        """Unified exception handling and logging."""
        from logic.config import get_color
        from logic.audit.utils import AuditManager
        from logic.utils import cleanup_old_files
        
        if print_error:
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
        from logic.lang.utils import get_translation
        from logic.utils import get_logic_dir
        
        tool_internal = get_logic_dir(self.script_dir)
        # 1. Try tool-specific logic directory (e.g., tool/NAME/logic/)
        res = get_translation(str(tool_internal), key, None)
        if res and res != key: return res # Found in tool
        
        # 2. Try tool's logic directory (e.g., tool/NAME/logic/) - some tools use this
        res = get_translation(str(tool_internal), key, None)
        if res and res != key: return res
        
        # 3. Fallback to root project translations (logic/translation/*.json)
        return get_translation(str(self.project_root / "logic"), key, default)

    def setup_gui(self):
        """Centralized GUI environment setup."""
        from logic.gui.engine import setup_gui_environment
        setup_gui_environment()

