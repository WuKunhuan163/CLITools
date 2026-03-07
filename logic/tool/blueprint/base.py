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
        self.no_warning = "--no-warning" in sys.argv

        import inspect
        caller_file = Path(inspect.stack()[1].filename).resolve()

        from logic.resolve import setup_paths, find_project_root, get_tool_module_path
        self.project_root = setup_paths(caller_file)

        curr = caller_file.parent
        self.tool_dir = curr
        while curr != curr.parent and curr != self.project_root.parent:
            if (curr / "tool.json").exists():
                self.tool_dir = curr
                break
            curr = curr.parent

        self.script_dir = self.tool_dir
        self.tool_module_path = get_tool_module_path(self.tool_dir, self.project_root)
            
        self.tool_json_path = self.tool_dir / "tool.json"
        self.dependencies = []
        self._load_metadata()
        
        # Load tool-specific config for CPU limits
        self._cpu_limit = None
        self._cpu_timeout = None
        self._load_tool_config()
        
        # Auto-reexecute with correct python if PYTHON is a dependency
        # Must happen BEFORE setting sys.argv[0], since execve uses it
        if "PYTHON" in self.dependencies:
            from logic.utils import check_and_reexecute_with_python
            check_and_reexecute_with_python(self.tool_name)

        # Set argv[0] so argparse shows the tool name in usage text
        sys.argv[0] = self.tool_name

    def _load_tool_config(self):
        """Load tool-specific configuration, including CPU limits."""
        config_path = self.get_data_dir() / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self._cpu_limit = config.get("cpu_limit")
                    self._cpu_timeout = config.get("cpu_timeout")
            except Exception:
                pass

    def get_cpu_limit(self):
        """Get the tool's configured CPU limit, falling back to global if not set."""
        if self._cpu_limit is not None:
            return self._cpu_limit
        from logic.config import get_setting
        return get_setting("test_cpu_limit", 80.0) # Default to 80%

    def get_cpu_timeout(self):
        """Get the tool's configured CPU timeout, falling back to global if not set."""
        if self._cpu_timeout is not None:
            return self._cpu_timeout
        from logic.config import get_setting
        return get_setting("test_cpu_timeout", 30) # Default to 30 seconds

    def check_cpu_load_and_warn(self):
        """Check current CPU load and issue a warning if it exceeds the tool's limit."""
        if self.no_warning:
            return
        
        from logic.utils import get_cpu_percent
        from logic.config import get_color
        
        current_cpu = get_cpu_percent(interval=0.1)
        cpu_limit = self.get_cpu_limit()
        
        if current_cpu > cpu_limit:
            YELLOW = get_color("YELLOW", "\033[33m")
            BOLD = get_color("BOLD", "\033[1m")
            RESET = get_color("RESET", "\033[0m")
            
            warning_label = self.get_translation("label_warning", "Warning")
            msg_rest = self.get_translation("warn_cpu_load_rest", "Current CPU load ({current_cpu:.1f}%) exceeds tool's recommended limit ({cpu_limit:.1f}%). Performance may be affected.").format(current_cpu=current_cpu, cpu_limit=cpu_limit)
            sys.stdout.write(f"\r\033[K{BOLD}{YELLOW}{warning_label}{RESET}: {msg_rest}\n")
            sys.stdout.flush()

    def get_data_dir(self):
        """Returns the data directory for this tool, respecting nesting."""
        return self.tool_dir / "data"

    def get_log_dir(self):
        """Returns the log directory for this tool, respecting nesting."""
        return self.get_data_dir() / "log"

    def get_session_logger(self):
        """Returns the per-invocation SessionLogger, creating it lazily on first call."""
        if not hasattr(self, "_session_logger") or self._session_logger is None:
            from logic.utils import SessionLogger
            self._session_logger = SessionLogger(self.get_log_dir(), limit=64)
        return self._session_logger

    def log(self, message: str, extra: str = None, include_stack: bool = True):
        """Write a timestamped entry to the tool's session log file.
        Delegates to get_session_logger().write()."""
        self.get_session_logger().write(message, extra=extra, include_stack=include_stack)

    def create_progress_machine(self, stages=None, manager=None, **kwargs):
        """Create a ProgressTuringMachine pre-configured with this tool's settings."""
        from logic.turing.models.progress import ProgressTuringMachine
        return ProgressTuringMachine(
            stages=stages,
            project_root=self.project_root,
            tool_name=self.tool_name,
            log_dir=self.get_log_dir(),
            no_warning=self.no_warning,
            manager=manager,
            session_logger=self.get_session_logger(),
            **kwargs
        )

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
            # Dependencies are ALWAYS searched in the project root's tool/ directory
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
        """Get the directory path of another tool (at project root level)."""
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

    def handle_command_line(self, parser=None, dev_handler=None, test_handler=None):
        """Process command line arguments.

        Parameters
        ----------
        parser : argparse.ArgumentParser, optional
            The tool's own argument parser.
        dev_handler : callable(list[str]) -> None, optional
            Custom handler for ``--dev`` sub-commands.  Receives the
            arguments after ``--dev``.  When *None*, only the built-in
            dev commands (sanity-check, audit-test, info) are available.
        test_handler : callable(list[str]) -> None, optional
            Custom handler for ``--test`` sub-commands.  Receives the
            arguments after ``--test``.  When *None*, the default test
            runner is used.

        Returns True if a command was handled and the tool should exit.
        """
        self.check_cpu_load_and_warn()

        self.is_quiet = "--tool-quiet" in sys.argv

        sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a not in ["--no-warning", "--tool-quiet"]]

        # ---- --dev / --test flag intercept (before argparse) ----
        if "--dev" in sys.argv:
            idx = sys.argv.index("--dev")
            dev_args = sys.argv[idx + 1:]
            if dev_handler:
                dev_handler(dev_args)
            else:
                self._handle_default_dev(dev_args)
            return True

        if "--test" in sys.argv:
            idx = sys.argv.index("--test")
            test_args = sys.argv[idx + 1:]
            if test_handler:
                test_handler(test_args)
            else:
                self._handle_default_test(test_args)
            return True

        if len(sys.argv) > 1:
            args_to_check = sys.argv[1:]
            cmd = args_to_check[0]
            if not cmd: return False

            if cmd == "setup":
                self.run_setup()
                return True
            elif cmd in ["-h", "--help", "help"]:
                if parser:
                    parser.print_help()
                else:
                    self.print_default_help()
                return True
            elif cmd == "install":
                if len(args_to_check) > 1:
                    subtool_name = args_to_check[1]
                    self.run_subtool_install(subtool_name)
                else:
                    print(f"Usage: {self.tool_name} install <SUBTOOL_NAME>")
                return True
            elif cmd == "uninstall":
                if len(args_to_check) > 1:
                    subtool_name = args_to_check[1]
                    force_yes = "-y" in args_to_check or "--yes" in args_to_check
                    self.run_subtool_uninstall(subtool_name, force_yes=force_yes)
                else:
                    print(f"Usage: {self.tool_name} uninstall <SUBTOOL_NAME> [-y]")
                return True
            elif cmd == "rule":
                self.print_rule()
                return True
            elif cmd == "skills":
                self._handle_skills_command(args_to_check[1:])
                return True
            elif cmd == "config":
                is_custom_config = False
                if parser:
                    for action in parser._actions:
                        if action.dest == 'command' and hasattr(action, 'choices') and 'config' in action.choices:
                            is_custom_config = True
                            break
                if not is_custom_config:
                    self._handle_tool_config(args_to_check[1:])
                    return True

            subtool_main = self.tool_dir / "tool" / cmd / "main.py"
            if not cmd.startswith("-") and subtool_main.exists():
                cmd_args = [sys.executable, str(subtool_main)] + args_to_check[1:]
                try:
                    res = subprocess.run(cmd_args)
                    sys.exit(res.returncode)
                except Exception as e:
                    print(f"Error executing subtool {cmd}: {e}")
                    sys.exit(1)

            if parser:
                import argparse
                is_recognized = False
                has_positional_nargs = False
                choices = []
                if cmd.startswith("-"):
                    is_recognized = True
                else:
                    for action in parser._actions:
                        if isinstance(action, argparse._SubParsersAction):
                            choices.extend(action.choices.keys())
                        elif action.choices:
                            choices.extend(action.choices)
                        if cmd in action.option_strings:
                            is_recognized = True
                        if (not action.option_strings
                                and action.nargs in ("*", "+", argparse.REMAINDER)):
                            has_positional_nargs = True
                    if cmd in choices: is_recognized = True
                    if cmd in ["-h", "--help"]: is_recognized = True

                if not is_recognized and not has_positional_nargs:
                    res = self.run_system_fallback(capture_output=self.is_quiet, filtered_args=args_to_check)
                    if res is None:
                        return True
                    if self.is_quiet:
                        print("TOOL_RESULT_JSON:" + json.dumps({
                            "returncode": res.returncode,
                            "stdout": res.stdout,
                            "stderr": res.stderr
                        }))
                        return True
                    return True
        return False

    # ------------------------------------------------------------------ #
    #  --dev / --test default handlers                                     #
    # ------------------------------------------------------------------ #

    def _handle_default_dev(self, args):
        """Built-in --dev commands available for every tool."""
        from logic.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        GREEN = get_color("GREEN", "\033[32m")
        BLUE = get_color("BLUE", "\033[34m")
        RESET = get_color("RESET", "\033[0m")

        subcmd = args[0] if args else ""

        if subcmd == "sanity-check":
            fix = "--fix" in args
            from logic.tool.dev.commands import dev_sanity_check
            dev_sanity_check(self.tool_name, self.project_root, fix=fix)
        elif subcmd == "audit-test":
            fix = "--fix" in args
            from logic.tool.dev.commands import dev_audit_test
            dev_audit_test(self.tool_name, self.project_root, fix=fix)
        elif subcmd == "info":
            print(f"\n{BOLD}{self.tool_name} Developer Info{RESET}")
            print(f"  tool_dir:        {self.tool_dir}")
            print(f"  project_root:    {self.project_root}")
            print(f"  module_path:     {self.tool_module_path}")
            print(f"  dependencies:    {', '.join(self.dependencies) or '(none)'}")
            print(f"  data_dir:        {self.get_data_dir()}")
            test_dir = self.tool_dir / "test"
            tests = list(test_dir.glob("test_*.py")) if test_dir.exists() else []
            print(f"  tests:           {len(tests)} file(s)")
            print()
        else:
            print(f"Usage: {self.tool_name} --dev <command>")
            print(f"\n{BOLD}Available commands:{RESET}")
            print(f"  sanity-check [--fix]   Check tool structure")
            print(f"  audit-test [--fix]     Audit unit test naming")
            print(f"  info                   Show tool developer info")

    def _handle_default_test(self, args):
        """Built-in --test handler: run this tool's unit tests."""
        import argparse as _ap
        tp = _ap.ArgumentParser(add_help=False)
        tp.add_argument("--range", nargs=2, type=int, help="Test range (start end)")
        tp.add_argument("--max", type=int, default=3, help="Max concurrent tests")
        tp.add_argument("--timeout", type=int, default=60, help="Timeout per test")
        tp.add_argument("--list", action="store_true", help="List tests only")
        tp.add_argument("--no-warning", action="store_true")
        test_args = tp.parse_args(args)

        test_args.tool_name = self.tool_name
        from logic.test.manager import test_tool_with_args
        test_tool_with_args(test_args, self.project_root)

    def _handle_tool_config(self, args):
        """Handle tool-specific configuration settings."""
        import argparse
        config_path = self.get_data_dir() / "config.json"
        config = {}
        if config_path.exists():
            try:
                with open(config_path, 'r') as f: config = json.load(f)
            except Exception: pass
        
        updated = False
        
        # Parse arguments for tool-specific config
        config_parser = argparse.ArgumentParser(add_help=False)
        config_parser.add_argument("--cpu-limit", type=float, help="Set CPU limit for this tool (e.g., 70.0)")
        config_parser.add_argument("--cpu-timeout", type=int, help="Set CPU wait timeout for this tool (seconds)")
        
        # Allow unknown args to pass through, but parse known ones
        known_args, unknown_args = config_parser.parse_known_args(args)
        
        if known_args.cpu_limit is not None:
            config["cpu_limit"] = known_args.cpu_limit
            updated = True
        if known_args.cpu_timeout is not None:
            config["cpu_timeout"] = known_args.cpu_timeout
            updated = True
        
        if updated:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            from logic.config import get_color
            BOLD, GREEN, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RESET")
            print(f"{BOLD}{GREEN}Successfully updated{RESET} {self.tool_name} configuration:")
            for k, v in config.items():
                print(f"  {k}: {v}")
        else:
            print(f"Usage: {self.tool_name} config [--cpu-limit <float>] [--cpu-timeout <int>]")

    def _get_tool_skills(self):
        """Get skills relevant to this tool from tool.json and tool-level skills/ directory."""
        skills = []
        # 1. From tool.json "skills" field
        if self.tool_json_path.exists():
            try:
                with open(self.tool_json_path, 'r') as f:
                    data = json.load(f)
                skills_list = data.get("skills", [])
                if isinstance(skills_list, list):
                    skills.extend(skills_list)
            except Exception:
                pass
        # 2. From tool-level skills/ directory
        tool_skills_dir = self.tool_dir / "skills"
        if tool_skills_dir.exists():
            for skill_dir in sorted(tool_skills_dir.iterdir()):
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    if skill_dir.name not in skills:
                        skills.append(skill_dir.name)
        return skills

    def _resolve_skill_path(self, name):
        """Find SKILL.md by name across all skill locations."""
        # 1. Tool-level skills/
        p = self.tool_dir / "skills" / name / "SKILL.md"
        if p.exists(): return p
        # 2. Project-level skills/
        p = self.project_root / "skills" / name / "SKILL.md"
        if p.exists(): return p
        # 3. SKILLS tool library
        p = self.project_root / "tool" / "SKILLS" / "data" / "library" / name / "SKILL.md"
        if p.exists(): return p
        return None

    def _handle_skills_command(self, args):
        """Handle 'TOOLNAME skills [show <name> | list | search <query>]' command."""
        from logic.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        GREEN = get_color("GREEN", "\033[32m")
        BLUE = get_color("BLUE", "\033[34m")
        YELLOW = get_color("YELLOW", "\033[33m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")

        tool_skills = self._get_tool_skills()
        subcmd = args[0] if args else "list"

        if subcmd == "show" and len(args) > 1:
            name = args[1]
            path = self._resolve_skill_path(name)
            if path:
                print(path.read_text())
            else:
                print(f"{BOLD}{RED}Error{RESET}: Skill '{name}' not found.")
            return

        if subcmd == "search" and len(args) > 1:
            query = " ".join(args[1:]).lower()
            library_dir = self.project_root / "tool" / "SKILLS" / "data" / "library"
            project_skills_dir = self.project_root / "skills"
            matches = []
            for source in [library_dir, project_skills_dir]:
                if not source.exists(): continue
                for skill_dir in sorted(source.iterdir()):
                    skill_file = skill_dir / "SKILL.md"
                    if not skill_dir.is_dir() or not skill_file.exists(): continue
                    content = skill_file.read_text()
                    if query in skill_dir.name.lower() or query in content.lower():
                        desc = ""
                        for line in content.splitlines():
                            if line.startswith("description:"):
                                desc = line[len("description:"):].strip()
                                break
                        matches.append((skill_dir.name, desc))
            if matches:
                print(f"{BOLD}Found {len(matches)} skill(s) matching '{query}':{RESET}\n")
                for name, desc in matches[:20]:
                    print(f"  {BOLD}{name}{RESET}")
                    if desc: print(f"    {desc}")
                if len(matches) > 20:
                    print(f"\n  ... and {len(matches) - 20} more.")
            else:
                print(f"No skills found matching '{query}'.")
            return

        # Default: list skills for this tool
        if subcmd == "list" or not args:
            if tool_skills:
                print(f"\n{BOLD}{self.tool_name} Skills:{RESET}\n")
                for name in tool_skills:
                    path = self._resolve_skill_path(name)
                    desc = ""
                    if path:
                        for line in path.read_text().splitlines():
                            if line.startswith("description:"):
                                desc = line[len("description:"):].strip()
                                break
                    status = f"{GREEN}available{RESET}" if path else f"{YELLOW}not found{RESET}"
                    print(f"  {BOLD}{name}{RESET}  [{status}]")
                    if desc: print(f"    {desc}")
                print(f"\n  Use '{self.tool_name} skills show <name>' to view a skill.")
            else:
                print(f"{self.tool_name} has no tool-specific skills configured.")
                print(f"Use '{self.tool_name} skills search <query>' to find skills from the library.")
            return

        print(f"Usage: {self.tool_name} skills [list | show <name> | search <query>]")

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
                
            except Exception as e:
                print(f"Error reading tool metadata: {e}")
        else:
            print(f"No metadata found for {self.tool_name}")

        # AI Agent critical instruction for USERINPUT
        if self.tool_name == "USERINPUT":
            instruction = self.get_translation("ai_instruction", "## Critical Directive: Feedback Acquisition\n...")
            print("\n" + instruction)
            
            # Additional hint for interruptions
            interruption_hint = self.get_translation("msg_interruption_hint", "\nNote: If your command execution was interrupted, aborted, or cancelled (e.g., Error: Command failed to spawn: Aborted), you MUST run USERINPUT immediately to check for user feedback before exiting or proceeding.")
            print(interruption_hint)
        
        print("--------------------------")

    def run_setup(self):
        """Execute the tool's setup.py script using ProgressTuringMachine."""
        from logic.turing.models.progress import ProgressTuringMachine
        from logic.turing.logic import TuringStage
        from logic.config import get_color
        
        setup_script = self.tool_dir / "setup.py"
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

        tm = ProgressTuringMachine(project_root=self.project_root, tool_name=self.tool_name, no_warning=self.no_warning)
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
        """Unified exception handling and logging.
        Writes the full traceback into the current session log file."""
        from logic.config import get_color
        
        if print_error:
            RED = get_color("RED", "\033[31m")
            BOLD = get_color("BOLD", "\033[1m")
            RESET = get_color("RESET", "\033[0m")
            
        error_msg = f"{BOLD}{RED}Error{RESET}: {str(e)}"
        print(error_msg, file=sys.stderr, flush=True)
        
        hint = self.get_translation("msg_interruption_hint", "\nNote: If your command execution was interrupted, aborted, or cancelled (e.g., Error: Command failed to spawn: Aborted), you MUST run USERINPUT immediately to check for user feedback before exiting or proceeding.")
        print(hint, file=sys.stderr, flush=True)

        logger = self.get_session_logger()
        logger.write_exception(e, context=f"Unhandled exception in {self.tool_name}")

    def get_translation(self, key, default, **kwargs):
        """Get tool-specific translation with fallback to root."""
        from logic.lang.utils import get_translation
        from logic.utils import get_logic_dir
        
        tool_internal = get_logic_dir(self.tool_dir)
        # 1. Try tool-specific logic directory (e.g., tool/NAME/logic/)
        res = get_translation(str(tool_internal), key, None, **kwargs)
        if res and res != key: return res # Found in tool
        
        # 2. Try tool's logic directory (e.g., tool/NAME/logic/) - some tools use this
        res = get_translation(str(tool_internal), key, None, **kwargs)
        if res and res != key: return res
        
        # 3. Fallback to root project translations (logic/translation/*.json)
        return get_translation(str(self.project_root / "logic"), key, default, **kwargs)

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
        
        # Subtools use the naming convention: PARENT.SUBTOOL
        # and are stored directly in the project root's tool/ directory.
        subtool_full_name = f"{self.tool_name}.{subtool_name}"
        engine = ToolEngine(subtool_full_name, self.project_root)
        
        if engine.install():
            return True
        return False

    def run_subtool_uninstall(self, subtool_name, force_yes=False):
        """Standardized sub-tool uninstallation logic."""
        subtool_full_name = f"{self.tool_name}.{subtool_name}"
        subtool_dir = self.project_root / "tool" / subtool_full_name
        
        if not subtool_dir.exists():
            from logic.config import get_color
            RED = get_color("RED", "\033[31m")
            BOLD = get_color("BOLD", "\033[1m")
            RESET = get_color("RESET", "\033[0m")
            print(f"{BOLD}{RED}Error{RESET}: Sub-tool '{subtool_name}' ({subtool_full_name}) is not installed.")
            return False

        if not force_yes:
            from logic.lang.utils import get_translation
            gui_logic_dir = str(self.project_root / "logic")
            confirm_msg = get_translation(gui_logic_dir, "confirm_uninstall", "Are you sure you want to uninstall '{name}'? (y/N): ", name=subtool_full_name)
            
            confirm = input(confirm_msg)
            # Erase prompt
            sys.stdout.write(f"\033[A\r\033[K")
            sys.stdout.flush()
            
            if confirm.lower() not in ['y', 'yes']:
                print(get_translation(gui_logic_dir, "uninstall_cancelled", "Uninstall cancelled."))
                return False

        from logic.tool.setup.engine import ToolEngine
        engine = ToolEngine(subtool_full_name, self.project_root)
        return engine.uninstall()

    def print_default_help(self):
        """Print a default help message if no parser is provided."""
        from logic.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        RESET = get_color("RESET", "\033[0m")
        
        print(f"Usage: {self.tool_name} <command> [options]")
        print(f"\n{BOLD}Built-in commands:{RESET}")
        print(f"  setup        Run tool installation/setup")
        print(f"  install      Install a sub-tool")
        print(f"  uninstall    Uninstall a sub-tool")
        print(f"  config       Manage tool configuration")
        print(f"  rule         Show AI rules for this tool")
        print(f"  -h, --help   Show this help message")

    def raise_success_status(self, action_msg):
        """Unified success status reporting for tools."""
        from logic.utils import print_success_status
        print_success_status(action_msg)

    def print_result_if_quiet(self, returncode, stdout="", stderr=""):
        """Print JSON result if quiet mode is active."""
        if getattr(self, "is_quiet", False):
            print("TOOL_RESULT_JSON:" + json.dumps({
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr
            }))
