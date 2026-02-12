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
        
        # Robust project root detection: find the directory containing 'bin/TOOL' or 'tool.json' (root)
        def find_root(start_path):
            curr = start_path
            while curr != curr.parent:
                if (curr / "bin" / "TOOL").exists() or ((curr / "tool.json").exists() and curr.parent.name != "tool" and curr.name != "tool"):
                    # Additional check to avoid misidentifying subtool dir as root
                    if (curr / "tool.json").exists() and (curr / "bin").exists():
                        return curr
                curr = curr.parent
            # Fallback to the old logic if nothing found
            return start_path.parent.parent
            
        self.project_root = find_root(self.script_dir)
        
        # Ensure project root is in path for imports
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))
            
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
            
            error_label = self.get_translation("label_error", "Error")
            for dep in missing:
                msg = self.get_translation("err_tool_not_found", "Tool '{dep_name}' not found, required by '{tool_name}'.").format(dep_name=dep, tool_name=self.tool_name)
                print(f"{BOLD}{RED}{error_label}{RESET}: {msg}")
                print(self.get_translation("err_tool_install_hint", "Please run: TOOL install {dep_name}").format(dep_name=dep))
            
            print(self.get_translation("err_tool_setup_hint", "Finally, run tool's setup: {tool_name} setup").format(tool_name=self.tool_name))
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

    def handle_command_line(self, parser=None):
        """
        Process command line arguments. 
        If 'setup' is the first argument, run the tool's setup.py.
        If 'install' is the first argument, handle sub-tool installation.
        If a parser is provided, attempts to determine if the command is recognized.
        If not recognized, delegates to system fallback.
        Returns True if a command was handled and the tool should exit.
        """
        if len(sys.argv) > 1:
            # Check for tool-specific quiet flag
            is_quiet = False
            args_to_check = sys.argv[1:]
            if "--tool-quiet" in args_to_check:
                is_quiet = True
                # Create a copy of args without the flag for further processing
                args_to_check = [a for p, a in enumerate(sys.argv[1:]) if a != "--tool-quiet"]

            cmd = args_to_check[0] if args_to_check else None
            if not cmd: return False

            if cmd == "setup":
                self.run_setup()
                return True
            elif cmd == "install":
                if len(args_to_check) > 1:
                    subtool_name = args_to_check[1]
                    self.run_subtool_install(subtool_name)
                else:
                    print(f"Usage: {self.tool_name} install <SUBTOOL_NAME>")
                return True
            elif cmd == "rule":
                self.print_rule()
                return True
            
            # 2. Check if it's a subtool
            subtool_main = self.script_dir / "tool" / cmd / "main.py"
            if subtool_main.exists():
                # Proxy to subtool
                cmd_args = [sys.executable, str(subtool_main)] + args_to_check[1:]
                try:
                    res = subprocess.run(cmd_args)
                    sys.exit(res.returncode)
                except Exception as e:
                    print(f"Error executing subtool {cmd}: {e}")
                    sys.exit(1)

            # 3. Check against parser if provided
            if parser:
                import argparse
                
                # Check if it's a known sub-command or flag
                is_recognized = False
                choices = []
                for action in parser._actions:
                    if isinstance(action, argparse._SubParsersAction):
                        choices.extend(action.choices.keys())
                    if cmd in action.option_strings:
                        is_recognized = True
                
                if cmd in choices:
                    is_recognized = True
                
                # Special cases for help
                if cmd in ["-h", "--help"]:
                    is_recognized = True

                if not is_recognized:
                    # Not a recognized tool command, delegate to system
                    res = self.run_system_fallback(capture_output=is_quiet, filtered_args=args_to_check)
                    if is_quiet:
                        # Print JSON result for interface use
                        print("TOOL_RESULT_JSON:" + json.dumps({
                            "returncode": res.returncode,
                            "stdout": res.stdout,
                            "stderr": res.stderr
                        }))
                        return True
                    return True
        return False

    def run_system_fallback(self, capture_output=False, filtered_args=None):
        """Delegate unknown commands to the system equivalent."""
        import subprocess
        import shutil
        
        # Mapping for specific tools that act as wrappers
        mapping = {
            "GIT": "/usr/bin/git",
            "PYTHON": sys.executable 
        }
        
        system_cmd = mapping.get(self.tool_name.upper())
        if not system_cmd:
            original_path = os.environ.get("PATH", "")
            our_bin = str(self.project_root / "bin")
            filtered_path = os.pathsep.join([p for p in original_path.split(os.pathsep) if p != our_bin])
            system_cmd = shutil.which(self.tool_name.lower(), path=filtered_path)
        
        if not system_cmd:
            print(f"Unknown command '{sys.argv[1]}' for {self.tool_name}. No system fallback found.")
            return None

        cmd = [system_cmd] + (filtered_args if filtered_args is not None else sys.argv[1:])
        try:
            env = os.environ.copy()
            our_bin = str(self.project_root / "bin")
            env["PATH"] = os.pathsep.join([p for p in env.get("PATH", "").split(os.pathsep) if p != our_bin])
            
            if capture_output:
                res = subprocess.run(cmd, env=env, capture_output=True, text=True)
                return res
            else:
                res = subprocess.run(cmd, env=env)
                sys.exit(res.returncode)
        except Exception as e:
            print(f"Error executing system fallback for {self.tool_name} ({system_cmd}): {e}")
            sys.exit(1)

    def print_rule(self):
        """Print tool-specific rules from tool.json."""
        from logic.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        BLUE = get_color("BLUE", "\033[34m")
        RESET = get_color("RESET", "\033[0m")
        
        print(f"--- {BOLD}{self.tool_name}{RESET} Rule ---")
        
        if self.tool_json_path.exists():
            try:
                with open(self.tool_json_path, 'r') as f:
                    data = json.load(f)
                    
                desc = self.get_translation(f"tool_{self.tool_name}_desc", data.get('description', 'No description'))
                purpose = self.get_translation(f"tool_{self.tool_name}_purpose", data.get('purpose', 'No purpose'))
                usage = data.get('usage', [])
                
                print(f"{BOLD}Description{RESET}: {desc}")
                print(f"{BOLD}Purpose{RESET}: {purpose}")
                
                if usage:
                    print(f"\n{BOLD}Usage{RESET}:")
                    for line in usage:
                        print(f"- {line}")
                
                # AI Agent critical instruction for USERINPUT
                if self.tool_name == "USERINPUT":
                    print("\n" + self.get_translation("ai_instruction", "## Critical Directive: Feedback Acquisition\n..."))
                    
            except Exception as e:
                print(f"Error reading tool metadata: {e}")
        else:
            print(f"No metadata found for {self.tool_name}")
        
        print("--------------------------")

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

        tm = ProgressTuringMachine(project_root=self.project_root, tool_name=self.tool_name)
        # "Running setup" should be blue and bold. 
        # In ProgressTuringMachine, active_status is colored and bolded.
        tm.add_stage(TuringStage(
            name=self.get_translation("label_the_tool_setup", "for the {name} tool").format(name=self.tool_name),
            action=run_setup_action,
            active_status=self.get_translation("label_running_setup", "Running setup"),
            success_status=self.get_translation("label_success", "Successfully"),
            fail_status=self.get_translation("label_failed_to_setup", "Failed to setup"),
            success_name=self.get_translation("label_setup_success_name", "setup {name} tool").format(name=self.tool_name),
            fail_name=self.get_translation("label_the_tool_name", "the {name} tool").format(name=self.tool_name),
            bold_part="setup"
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

    def get_color(self, color_name, default=""):
        """Get color from global config."""
        from logic.config import get_color
        return get_color(color_name, default)

    def setup_gui(self):
        """Centralized GUI environment setup."""
        from logic.gui.engine import setup_gui_environment
        setup_gui_environment()

    def run_gui(self, python_exe, script_path, timeout, custom_id=None):
        """Unified method to launch a GUI subprocess and wait for its result."""
        from logic.gui.manager import run_gui_subprocess
        return run_gui_subprocess(self, python_exe, script_path, timeout, custom_id)

    def run_gui_with_fallback(self, python_exe, script_path, timeout, custom_id=None, hint=None):
        """Standard GUI launch with automatic sandbox fallback."""
        from logic.gui.engine import is_sandboxed
        
        # 1. Try standard GUI
        res = self.run_gui(python_exe, script_path, timeout, custom_id)
        
        # 2. Check for sandbox failure
        if res.get("status") == "error" and is_sandboxed():
            # Check if it's a display related error
            err_msg = str(res.get("message", res.get("data", "")))
            # Expanded list of sandbox indicators
            is_display_err = any(msg in err_msg.lower() or msg in err_msg for msg in ["display", "NSInternalInconsistencyException", "Connection invalid", "Unknown error", "physical blocking", "sandbox", "tk.tcl"])
            
            if is_display_err:
                initial_content = self.get_fallback_initial_content(hint)
                raw_result = self.handle_sandbox_fallback(initial_content, timeout)
                
                if raw_result == "__FALLBACK_INTERRUPTED__":
                    return {"status": "terminated", "reason": "interrupted", "data": None}
                elif raw_result == "__FALLBACK_TIMEOUT__":
                    return {"status": "timeout", "data": None}
                elif raw_result is not None:
                    processed = self.process_fallback_result(raw_result)
                    return {"status": "success", "data": processed}
                else:
                    return {"status": "terminated", "reason": "interrupted", "data": None}
        
        return res

    def handle_sandbox_fallback(self, initial_content, timeout):
        """Default fallback implementation using text files."""
        from logic.gui.manager import run_file_fallback
        return run_file_fallback(self, initial_content, timeout)

    def get_fallback_initial_content(self, hint):
        """Hook for tools to customize initial fallback file content."""
        return hint or ""

    def run_subtool_install(self, subtool_name):
        """Standardized sub-tool installation logic."""
        from logic.tool.setup.engine import ToolEngine
        
        # Subtools are stored in tool/PARENT/tool/SUBTOOL
        subtool_parent_dir = self.script_dir / "tool"
        engine = ToolEngine(subtool_name, self.project_root, parent_tool_dir=subtool_parent_dir)
        
        if engine.install():
            # If successful, sub-tool is now in tool/PARENT/tool/SUBTOOL
            return True
        return False
