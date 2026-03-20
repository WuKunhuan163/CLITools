import os
import sys
import subprocess
from pathlib import Path
import json

class ToolBase:
    """Base class for all tools to handle dependencies, common utilities, and exception logging."""
    
    def __init__(self, tool_name, is_root=False):
        self.tool_name = tool_name
        self.is_root = is_root
        self.no_warning = "--no-warning" in sys.argv

        import inspect
        caller_file = Path(inspect.stack()[1].filename).resolve()

        from logic.resolve import setup_paths, get_tool_module_path
        self.project_root = setup_paths(caller_file)

        if is_root:
            self.tool_dir = self.project_root
        else:
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
        if not is_root:
            self._load_metadata()
        
        self._cpu_limit = None
        self._cpu_timeout = None
        self._load_tool_config()
        
        self._hooks_engine = None

        if not is_root and "PYTHON" in self.dependencies:
            from logic.utils import check_and_reexecute_with_python
            check_and_reexecute_with_python(self.tool_name)

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
        from logic._.config import get_setting
        return get_setting("test_cpu_limit", 80.0) # Default to 80%

    def get_cpu_timeout(self):
        """Get the tool's configured CPU timeout, falling back to global if not set."""
        if self._cpu_timeout is not None:
            return self._cpu_timeout
        from logic._.config import get_setting
        return get_setting("test_cpu_timeout", 30) # Default to 30 seconds

    def check_cpu_load_and_warn(self):
        """Check current CPU load and issue a warning if it exceeds the tool's limit."""
        if self.no_warning:
            return
        
        from logic.utils import get_cpu_percent
        from logic._.config import get_color
        
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

    # ------------------------------------------------------------------ #
    #  Hooks                                                               #
    # ------------------------------------------------------------------ #

    def get_hooks_engine(self):
        """Return the HooksEngine for this tool, creating it lazily."""
        if self._hooks_engine is None:
            from logic._.hooks.engine import HooksEngine
            self._hooks_engine = HooksEngine(
                self.tool_dir, tool_name=self.tool_name,
                project_root=self.project_root,
            )
        return self._hooks_engine

    def fire_hook(self, event_name: str, **kwargs):
        """Fire a hook event. kwargs are passed to all enabled handlers.

        Automatically injects ``tool=self`` if not already present.
        Returns a list of handler results, or [] if no handlers.
        """
        kwargs.setdefault("tool", self)
        engine = self.get_hooks_engine()
        return engine.fire(event_name, **kwargs)

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
            from logic._.config import get_color
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

        # ---- Rewrite --mcp-* to bare subcommands for argparse ----
        sys.argv = [sys.argv[0]] + [
            a[6:] if a.startswith("--mcp-") else a
            for a in sys.argv[1:]
        ]

        # ---- Framework flag intercepts (--prefixed, before argparse) ----
        def _extract_flag_args(flag):
            """Extract arguments after a --flag from sys.argv."""
            if flag in sys.argv:
                idx = sys.argv.index(flag)
                return sys.argv[idx + 1:]
            return None

        dev_args = _extract_flag_args("--dev")
        if dev_args is not None:
            (dev_handler or self._handle_default_dev)(dev_args)
            return True

        test_args = _extract_flag_args("--test")
        if test_args is not None:
            (test_handler or self._handle_default_test)(test_args)
            return True

        if _extract_flag_args("--setup") is not None:
            self.run_setup()
            return True

        session_args = _extract_flag_args("--assistant")
        if session_args is not None:
            self._handle_assistant(session_args)
            return True

        endpoint_args = _extract_flag_args("--endpoint")
        if endpoint_args is not None:
            self._handle_endpoint(endpoint_args)
            return True

        from logic._.agent.command import ALLOW_ASSISTANT_SHORTHAND
        if ALLOW_ASSISTANT_SHORTHAND:
            agent_args = _extract_flag_args("--agent")
            if agent_args is not None:
                self._handle_agent(agent_args)
                return True

            ask_args = _extract_flag_args("--ask")
            if ask_args is not None:
                self._handle_agent(ask_args, mode="ask")
                return True

            plan_args = _extract_flag_args("--plan")
            if plan_args is not None:
                self._handle_agent(plan_args, mode="plan")
                return True

        if _extract_flag_args("--rule") is not None:
            self.print_rule()
            return True

        config_args = _extract_flag_args("--config")
        if config_args is not None:
            is_custom_config = False
            if parser:
                for action in parser._actions:
                    if action.dest == 'command' and hasattr(action, 'choices') and 'config' in action.choices:
                        is_custom_config = True
                        break
            if not is_custom_config:
                self._handle_tool_config(config_args)
                return True

        install_args = _extract_flag_args("--install")
        if install_args is not None:
            if install_args:
                self.run_subtool_install(install_args[0])
            else:
                print(f"Usage: {self.tool_name} --install <SUBTOOL_NAME>")
            return True

        uninstall_args = _extract_flag_args("--uninstall")
        if uninstall_args is not None:
            if uninstall_args:
                force_yes = "-y" in uninstall_args or "--yes" in uninstall_args
                self.run_subtool_uninstall(uninstall_args[0], force_yes=force_yes)
            else:
                print(f"Usage: {self.tool_name} --uninstall <SUBTOOL_NAME> [-y]")
            return True

        skills_args = _extract_flag_args("--skills")
        if skills_args is not None:
            self._handle_skills_command(skills_args)
            return True

        hooks_args = _extract_flag_args("--hooks")
        if hooks_args is not None:
            self._handle_hooks_command(hooks_args)
            return True

        eco_args = _extract_flag_args("--eco")
        if eco_args is not None:
            self._handle_eco_command(eco_args)
            return True

        call_reg_args = _extract_flag_args("--call-register")
        if call_reg_args is not None:
            self._handle_call_register(call_reg_args)
            return True

        if len(sys.argv) > 1:
            args_to_check = sys.argv[1:]
            cmd = args_to_check[0]
            if not cmd: return False

            if cmd in ["-h", "--help", "help"]:
                if parser:
                    parser.print_help()
                else:
                    self.print_default_help()
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
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        get_color("GREEN", "\033[32m")
        get_color("BLUE", "\033[34m")
        RESET = get_color("RESET", "\033[0m")

        subcmd = args[0] if args else ""

        if subcmd == "sanity-check":
            fix = "--fix" in args
            from logic._.dev.commands import dev_sanity_check
            dev_sanity_check(self.tool_name, self.project_root, fix=fix)
        elif subcmd == "audit-test":
            fix = "--fix" in args
            from logic._.dev.commands import dev_audit_test
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
        elif subcmd == "migrate":
            self._handle_dev_migrate(args[1:])
        else:
            print(f"Usage: {self.tool_name} --dev <command>")
            print(f"\n{BOLD}Available commands:{RESET}")
            print(f"  sanity-check [--fix]   Check tool structure")
            print(f"  audit-test [--fix]     Audit unit test naming")
            print(f"  info                   Show tool developer info")
            print(f"  migrate <target>       Sync asset resources (logos, filetypes, all)")

    def _handle_dev_migrate(self, args):
        """Download/sync remote asset resources to local storage."""
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        DIM = get_color("DIM", "\033[2m")
        GREEN = get_color("GREEN", "\033[32m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")

        target = args[0] if args else ""
        force = "--force" in args

        if target not in ("logos", "filetypes", "all"):
            print(f"Usage: {self.tool_name} --dev migrate <logos|filetypes|all> [--force]")
            print(f"\n  {BOLD}logos{RESET}       Download LLM model & provider logos (lobehub)")
            print(f"  {BOLD}filetypes{RESET}   Download file type icons (devicon)")
            print(f"  {BOLD}all{RESET}         Download everything")
            print(f"  {BOLD}--force{RESET}     Re-download existing files")
            return

        from logic.asset.migrate import migrate_logos, migrate_filetypes, migrate_all

        synced = 0
        if target == "logos":
            d, s, e = migrate_logos(force)
        elif target == "filetypes":
            d, s, e = migrate_filetypes(force)
        else:
            result = migrate_all(force)
            d, s, e = result["downloaded"], result["skipped"], result["errors"]
            synced = result.get("synced_to_llm", 0)

        print(f"  {BOLD}{GREEN}Downloaded{RESET} {d} files, {DIM}skipped {s}{RESET}")
        if synced:
            print(f"  {BOLD}{GREEN}Synced{RESET} {synced} logos to LLM tool directories")
        if e:
            print(f"  {BOLD}{RED}Failed{RESET} {len(e)}: {DIM}{', '.join(e[:10])}{RESET}")

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
        from logic._.test.manager import test_tool_with_args
        test_tool_with_args(test_args, self.project_root)

    def _handle_tool_config(self, args):
        """Handle tool-specific configuration settings.

        Invoked via ``TOOL --config [options]`` or ``TOOL config [options]``.

        Sub-commands:
            --config --assistant [KEY [VALUE]]  Manage agent session parameters
            --config --show                   Show tool-specific config
            --config --cpu-limit N            Set CPU load limit
        """
        if args and args[0] == "--assistant":
            self._handle_assistant_config(args[1:])
            return

        import argparse
        config_path = self.get_data_dir() / "config.json"
        config = {}
        if config_path.exists():
            try:
                with open(config_path, 'r') as f: config = json.load(f)
            except Exception: pass

        config_parser = argparse.ArgumentParser(
            prog=f"{self.tool_name} --config",
            description=f"Configuration for {self.tool_name}",
        )
        config_parser.add_argument("--cpu-limit", type=float,
                                   help="Set CPU load limit (e.g., 70.0)")
        config_parser.add_argument("--cpu-timeout", type=int,
                                   help="Set CPU wait timeout in seconds")
        config_parser.add_argument("--show", action="store_true",
                                   help="Show current configuration")

        known_args, _ = config_parser.parse_known_args(args)

        if known_args.show or (not any(v is not None for k, v in vars(known_args).items()
                                       if k != "show")):
            from logic._.config import get_color
            BOLD, RESET = get_color("BOLD"), get_color("RESET")
            if config:
                print(f"{BOLD}{self.tool_name} configuration:{RESET}")
                for k, v in sorted(config.items()):
                    print(f"  {k}: {v}")
            else:
                print(f"{BOLD}No configuration set{RESET} for {self.tool_name}.")
            if not config or known_args.show:
                return

        updated = False
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

            from logic._.config import get_color
            BOLD, GREEN, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RESET")
            print(f"{BOLD}{GREEN}Successfully updated{RESET} {self.tool_name} configuration:")
            for k, v in sorted(config.items()):
                print(f"  {k}: {v}")

    def _handle_assistant_config(self, args):
        """Manage agent session configuration.

        Invoked via ``TOOL --config --assistant [KEY [VALUE]]``.
        Reads/writes the LLM tool's config store.
        """
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        DIM = get_color("DIM", "\033[2m")
        GREEN = get_color("GREEN", "\033[32m")
        RESET = get_color("RESET", "\033[0m")

        try:
            from tool.LLM.logic.config import load_config, save_config
        except ImportError:
            print(f"  {BOLD}LLM tool not available.{RESET}")
            return

        cfg = load_config()

        SESSION_KEYS = {
            "default_turn_limit": ("Default max rounds per task", 20),
            "max_input_tokens": ("Max input tokens per API call", 65536),
            "max_output_tokens": ("Max output tokens per API call", 16384),
            "max_context_tokens": ("Max context window tokens before trimming", 1048576),
            "max_read_chars": ("Max chars returned by read_file", 12000),
            "max_exec_chars": ("Max chars returned by exec output", 6000),
            "history_limit": ("Default events shown by --history", 20),
            "active_backend": ("Active model/provider", "auto"),
            "language": ("System prompt language (zh/en)", "en"),
        }

        if not args:
            print(f"  {BOLD}Session Configuration{RESET}")
            print()
            for key, (desc, default) in SESSION_KEYS.items():
                val = cfg.get(key)
                display = f"{GREEN}{val}{RESET}" if val is not None else f"{DIM}(default: {default}){RESET}"
                print(f"  {BOLD}{key}{RESET} = {display}")
                print(f"    {DIM}{desc}{RESET}")
            return

        key = args[0]
        if len(args) == 1:
            val = cfg.get(key)
            if val is not None:
                print(f"  {BOLD}{key}{RESET} = {GREEN}{val}{RESET}")
            elif key in SESSION_KEYS:
                _, default = SESSION_KEYS[key]
                print(f"  {BOLD}{key}{RESET} = {DIM}(default: {default}){RESET}")
            else:
                print(f"  {BOLD}{key}{RESET} = {DIM}(not set){RESET}")
            if key in SESSION_KEYS:
                print(f"  {DIM}{SESSION_KEYS[key][0]}{RESET}")
            return

        value = " ".join(args[1:])
        int_keys = {k for k, (_, d) in SESSION_KEYS.items() if isinstance(d, int)}
        if key in int_keys:
            try:
                value = int(value)
            except ValueError:
                print(f"  {BOLD}Invalid value.{RESET} {DIM}{key} requires an integer.{RESET}")
                return

        cfg[key] = value
        save_config(cfg)
        print(f"  {BOLD}Saved.{RESET} {DIM}{key} = {value}{RESET}")

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
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        GREEN = get_color("GREEN", "\033[32m")
        get_color("BLUE", "\033[34m")
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
            DIM = get_color("DIM", "\033[2m")
            query = " ".join(args[1:])
            try:
                from logic._.search.tools import search_skills
                results = search_skills(
                    self.project_root, query, top_k=10,
                    tool_name=self.tool_name,
                )
            except ImportError:
                results = []
            if results:
                print(f"{BOLD}Found {len(results)} skill(s) matching '{query}':{RESET}\n")
                for i, r in enumerate(results, 1):
                    meta = r.get("meta", {})
                    score_pct = int(r["score"] * 100)
                    tool_tag = f" (tool: {meta['tool']})" if meta.get("tool") else ""
                    print(f"  {BOLD}{i}. {r['id']}{RESET}{tool_tag} ({score_pct}%)")
                    print(f"     {DIM}{meta.get('path', '')}{RESET}")
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

    def _handle_eco_command(self, args):
        """Handle 'TOOLNAME --eco [search|skill|guide|tool|here|cmds|cmd]'.

        Per-tool ecosystem navigation. When invoked on a specific tool
        (e.g., LLM --eco), shows tool-level ecosystem info by default.
        All subcommands from TOOL eco are available here, scoped to this tool.
        """
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        GREEN = get_color("GREEN", "\033[32m")
        DIM = get_color("DIM", "\033[2m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")

        subcmd = args[0] if args else ""

        if subcmd in ("-h", "--help", "help"):
            print(f"\n{BOLD}{self.tool_name} --eco{RESET} — Ecosystem Navigation\n")
            print(f"  (no args)                    Tool overview (docs, interface, tests)")
            print(f"  search <query>               Search scoped to {self.tool_name}")
            print(f"  skill <name>                 Read a skill")
            print(f"  here                         Context-aware help")
            print(f"  guide                        Onboarding guide")
            print(f"  cmds                         Blueprint shortcuts")
            print(f"  cmd <name>                   Run a blueprint shortcut")
            print()
            return

        if subcmd == "search" and len(args) > 1:
            query = " ".join(args[1:])
            try:
                from interface.eco import eco_search
                results = eco_search(self.project_root, query, tool=self.tool_name)
                if not results:
                    print(f"  No results for: {query}")
                    return
                for i, r in enumerate(results, 1):
                    meta = r.get("meta", {})
                    score_pct = int(r["score"] * 100)
                    rtype = meta.get("type", "unknown")
                    print(f"  {BOLD}{i}. {r['id']}{RESET} ({score_pct}%) [{rtype}]")
                    preview = meta.get("preview", "") or meta.get("description", "") or meta.get("lesson", "")
                    if preview:
                        print(f"     {DIM}{preview[:100]}{RESET}")
            except Exception as e:
                print(f"  {RED}Search error:{RESET} {e}")
            return

        if subcmd == "skill" and len(args) > 1:
            name = args[1]
            try:
                from interface.eco import eco_skill
                content = eco_skill(self.project_root, name)
                if content:
                    print(content)
                else:
                    print(f"  {BOLD}{RED}Not found:{RESET} {name}")
            except Exception as e:
                print(f"  {RED}Error:{RESET} {e}")
            return

        # Pass through to TOOL eco for global subcommands
        if subcmd in ("guide", "map", "recall", "cmds", "cmd"):
            import subprocess as _sp
            cmd_args = [sys.executable, str(self.project_root / "bin" / "TOOL"), "--eco"] + args
            _sp.run(cmd_args)
            return

        if subcmd == "here":
            try:
                from interface.eco import eco_here
                import os
                ctx = eco_here(self.project_root, os.getcwd())
                print(f"\n  {BOLD}CWD:{RESET} {ctx['cwd']}")
                print(f"  {BOLD}Level:{RESET} {ctx.get('level', '?')}")
                if ctx.get("docs"):
                    print(f"\n  {BOLD}Docs:{RESET}")
                    for d in ctx["docs"]:
                        print(f"    {DIM}{d}{RESET}")
                if ctx.get("actions"):
                    print(f"\n  {BOLD}Suggested:{RESET}")
                    for a in ctx["actions"]:
                        print(f"    {a}")
                print()
            except Exception as e:
                print(f"  {RED}Error:{RESET} {e}")
            return

        # Default: show this tool's ecosystem info
        if not subcmd or subcmd == "info":
            try:
                from interface.eco import eco_tool
                info = eco_tool(self.project_root, self.tool_name)
                if info:
                    print(f"\n  {BOLD}{info['name']}{RESET}")
                    if info.get("description"):
                        print(f"  {info['description']}")
                    print()
                    for label, ok in [
                        ("README.md", info.get("has_readme")),
                        ("for_agent.md", info.get("has_for_agent")),
                        ("interface/main.py", info.get("has_interface")),
                        ("hooks/", info.get("has_hooks")),
                        ("test/", info.get("has_tests")),
                    ]:
                        marker = f"{GREEN}✓{RESET}" if ok else f"{DIM}·{RESET}"
                        print(f"  {marker} {label}")
                    if info.get("interface_functions"):
                        print(f"\n  {BOLD}Interface:{RESET}")
                        for fn in info["interface_functions"][:10]:
                            print(f"    {fn}()")
                    print(f"\n  {BOLD}Actions:{RESET}")
                    print(f"    {self.tool_name} --eco search \"query\"")
                    if info.get("has_for_agent"):
                        print(f"    Read: tool/{self.tool_name}/for_agent.md")
                    print()
                else:
                    print(f"  {BOLD}{self.tool_name}{RESET}: no tool info available.")
            except Exception as e:
                print(f"  {RED}Error:{RESET} {e}")
            return

        # Unknown subcmd
        from logic.utils.fuzzy import suggest_commands
        known = ["search", "skill", "guide", "map", "here", "recall", "cmds", "cmd", "info"]
        matches = suggest_commands(subcmd, known, n=2, cutoff=0.4)
        if matches:
            print(f"  {BOLD}Unknown:{RESET} {subcmd}. Did you mean: {', '.join(matches)}?")
        else:
            print(f"  {BOLD}Unknown:{RESET} {subcmd}")
        print(f"  {DIM}{self.tool_name} --eco --help for available commands.{RESET}")

    def _handle_call_register(self, args):
        """Handle --call-register: register an upcoming tool call with semantic description.

        This fires the before_tool_call hook, which triggers skills matching.
        Usage: TOOL_NAME --call-register "description of what I'm about to do"
               TOOL_NAME --call-register --rounds 5  (grant 5 subsequent calls without re-registering)
               TOOL_NAME --call-register --status     (show current registration status)
               TOOL_NAME --call-register --off         (disable call-register requirement)
               TOOL_NAME --call-register --on          (enable call-register requirement)
        """
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        DIM = get_color("DIM", "\033[2m")
        GREEN = get_color("GREEN", "\033[32m")
        RESET = get_color("RESET", "\033[0m")

        reg_file = Path("/tmp") / f"call-register-{self.tool_name}"

        if "--off" in args:
            config_file = self.get_data_dir() / "config.json"
            cfg = {}
            if config_file.exists():
                try:
                    cfg = json.loads(config_file.read_text())
                except Exception:
                    pass
            cfg["call_register_enabled"] = False
            config_file.write_text(json.dumps(cfg, indent=2))
            print(f"  {BOLD}Call-register disabled.{RESET}")
            return

        if "--on" in args:
            config_file = self.get_data_dir() / "config.json"
            cfg = {}
            if config_file.exists():
                try:
                    cfg = json.loads(config_file.read_text())
                except Exception:
                    pass
            cfg["call_register_enabled"] = True
            config_file.write_text(json.dumps(cfg, indent=2))
            print(f"  {BOLD}Call-register enabled.{RESET}")
            return

        if "--status" in args:
            remaining = 0
            if reg_file.exists():
                try:
                    data = json.loads(reg_file.read_text())
                    remaining = data.get("remaining", 0)
                except Exception:
                    pass
            print(f"  {BOLD}Call-register{RESET} {DIM}remaining calls: {remaining}{RESET}")
            return

        rounds = 1
        description_parts = []
        i = 0
        while i < len(args):
            if args[i] == "--rounds" and i + 1 < len(args):
                try:
                    rounds = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            elif not args[i].startswith("--"):
                description_parts.append(args[i])
                i += 1
            else:
                i += 1

        description = " ".join(description_parts)
        if not description:
            print(f"  Usage: {self.tool_name} --call-register \"description\" [--rounds N]")
            return

        reg_data = {"remaining": rounds, "description": description}
        reg_file.write_text(json.dumps(reg_data))

        results = self.fire_hook("before_tool_call",
                                 command=description,
                                 description=description)

        matched_skills = []
        for r in results:
            if isinstance(r, dict) and r.get("matched_skills"):
                matched_skills.extend(r["matched_skills"])

        print(f"  {BOLD}{GREEN}Registered.{RESET} {DIM}{rounds} call(s) granted.{RESET}")
        if matched_skills:
            print(f"  {BOLD}Relevant skills:{RESET}")
            for s in matched_skills[:5]:
                print(f"    - {s['name']}: {DIM}{s['description'][:80]}{RESET}")
            print(f"  {DIM}Load with: SKILLS show <name>{RESET}")
        else:
            print(f"  {DIM}No matching skills found.{RESET}")

    def check_call_register(self) -> bool:
        """Check if --call-register is required and has remaining calls.

        Returns True if the tool can proceed, False if --call-register is needed first.
        """
        config_file = self.get_data_dir() / "config.json"
        enabled = True
        if config_file.exists():
            try:
                cfg = json.loads(config_file.read_text())
                enabled = cfg.get("call_register_enabled", True)
            except Exception:
                pass
        if not enabled:
            return True

        reg_file = Path("/tmp") / f"call-register-{self.tool_name}"
        if not reg_file.exists():
            return False
        try:
            data = json.loads(reg_file.read_text())
            remaining = data.get("remaining", 0)
            if remaining <= 0:
                return False
            data["remaining"] = remaining - 1
            reg_file.write_text(json.dumps(data))
            return True
        except Exception:
            return False

    def _handle_hooks_command(self, args):
        """Handle 'TOOLNAME hooks [list|show <name>|enable <name>|disable <name>]'."""
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        GREEN = get_color("GREEN", "\033[32m")
        get_color("BLUE", "\033[34m")
        YELLOW = get_color("YELLOW", "\033[33m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")

        engine = self.get_hooks_engine()
        subcmd = args[0] if args else "list"

        if subcmd == "list" or not args:
            interfaces = engine.list_interfaces()
            instances = engine.list_instances()

            if interfaces:
                print(f"\n{BOLD}{self.tool_name} Hook Events:{RESET}\n")
                for iface in interfaces:
                    print(f"  {BOLD}{iface['event_name']}{RESET}")
                    if iface['description']:
                        print(f"    {iface['description']}")

            if instances:
                print(f"\n{BOLD}{self.tool_name} Hook Instances:{RESET}\n")
                for inst in instances:
                    status = (f"{GREEN}enabled{RESET}" if inst['enabled']
                              else f"{YELLOW}disabled{RESET}")
                    default_tag = " (default)" if inst['enabled_by_default'] else ""
                    print(f"  {BOLD}{inst['name']}{RESET}  [{status}]{default_tag}")
                    print(f"    event: {inst['event_name']}")
                    if inst['description']:
                        print(f"    {inst['description']}")
            else:
                if not interfaces:
                    print(f"{self.tool_name} has no hooks configured.")
                    print(f"Create hooks in {self.tool_dir / 'hooks' / 'interface'}/")

            print(f"\n  Use '{self.tool_name} hooks enable <name>' to enable an instance.")
            print(f"  Use '{self.tool_name} hooks disable <name>' to disable an instance.")
            print(f"  Use '{self.tool_name} hooks show <name>' to inspect an instance.")
            return

        if subcmd == "show" and len(args) > 1:
            name = args[1]
            info = engine.get_instance_info(name)
            if info:
                status = (f"{GREEN}enabled{RESET}" if info['enabled']
                          else f"{YELLOW}disabled{RESET}")
                print(f"\n{BOLD}{info['name']}{RESET}  [{status}]")
                print(f"  event:       {info['event_name']}")
                print(f"  description: {info['description']}")
                print(f"  default:     {'yes' if info['enabled_by_default'] else 'no'}")
                if info.get('module_file'):
                    print(f"  file:        {info['module_file']}")
            else:
                print(f"{BOLD}{RED}Error{RESET}: Hook instance '{name}' not found.")
            return

        if subcmd == "enable" and len(args) > 1:
            name = args[1]
            if engine.enable(name):
                print(f"{BOLD}{GREEN}Enabled{RESET} hook instance '{name}'.")
            else:
                print(f"{BOLD}{RED}Error{RESET}: Hook instance '{name}' not found.")
            return

        if subcmd == "disable" and len(args) > 1:
            name = args[1]
            if engine.disable(name):
                print(f"{BOLD}{YELLOW}Disabled{RESET} hook instance '{name}'.")
            else:
                print(f"{BOLD}{RED}Error{RESET}: Hook instance '{name}' not found.")
            return

        print(f"Usage: {self.tool_name} hooks [list | show <name> | enable <name> | disable <name>]")

    @staticmethod
    def _get_system_git():
        """Resolve the real system git binary, avoiding PATH shadows."""
        try:
            from tool.GIT.interface.main import get_system_git
            return get_system_git()
        except ImportError:
            return "/usr/bin/git"

    def run_system_fallback(self, capture_output=False, filtered_args=None):
        """Delegate unknown commands to the system equivalent."""
        import subprocess
        import shutil
        
        # Mapping for specific tools that act as wrappers
        mapping = {
            "GIT": self._get_system_git(),
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
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        get_color("BLUE", "\033[34m")
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

    def _handle_agent(self, args, mode="agent"):
        """Dispatch --agent/--ask/--plan subcommands to the agent infrastructure."""
        from logic._.agent.command import handle_agent_command
        handle_agent_command(
            args=args,
            tool_name=self.tool_name,
            project_root=str(self.project_root),
            tool_dir=str(self.tool_dir),
            mode=mode,
        )

    def _handle_endpoint(self, args):
        """Dispatch ``--endpoint`` commands.  Override in subclasses.

        The default implementation raises ``EndpointNotImplemented`` and
        prints a user-friendly message.  Stateful tools (CDMCP, etc.)
        override this to expose structured JSON monitoring endpoints.

        See ``interface/endpoint.py`` for the ``EndpointRegistry`` helper
        and the symmetric interface contract.
        """
        from interface.endpoint import EndpointNotImplemented
        from logic._.config import get_color
        DIM = get_color("DIM", "\033[2m")
        RESET = get_color("RESET", "\033[0m")
        print(f"  {DIM}{self.tool_name} does not implement --endpoint. "
              f"Override _handle_endpoint() to add monitoring endpoints.{RESET}")

    def _handle_assistant(self, args):
        """Dispatch --assistant subcommands.

        Maps --assistant agent/ask/plan to --agent/--ask/--plan equivalents.
        Also handles --assistant checkout for switching active sessions.

        When called with no args, creates a new session and prints its ID
        along with the GUI port (if a server is running).
        """
        if not args:
            self._handle_assistant_create_and_info()
            return

        mode_flags = {"--agent": "agent", "--ask": "ask", "--plan": "plan"}
        mode = "agent"
        filtered = []
        i = 0
        while i < len(args):
            if args[i] in mode_flags:
                mode = mode_flags[args[i]]
            elif args[i] == "--prompt" and i + 1 < len(args):
                filtered.insert(0, "prompt")
                filtered.append(args[i + 1])
                i += 1
            else:
                filtered.append(args[i])
            i += 1

        subcmd = filtered[0] if filtered else ""
        rest = filtered[1:]

        if subcmd == "--endpoint" or subcmd == "endpoint":
            from logic._.agent.command import handle_assistant_endpoint
            handle_assistant_endpoint(rest, self.tool_name)
            return

        gui_api_cmds = {"list", "state", "history", "send", "model",
                        "edits", "accept", "revert", "accept-all",
                        "revert-all", "new", "delete", "clear", "cancel"}
        if subcmd in gui_api_cmds:
            from logic._.agent.command import handle_assistant_command
            handle_assistant_command(filtered, self.tool_name)
        elif subcmd in ("agent", "ask", "plan"):
            self._handle_agent(rest, mode=subcmd)
        elif subcmd == "gui":
            gui_pass = ["--gui"]
            j = 0
            while j < len(rest):
                if rest[j] == "--port" and j + 1 < len(rest):
                    j += 2
                elif rest[j] == "--no-auto":
                    j += 1
                else:
                    gui_pass.append(rest[j])
                    j += 1
            self._handle_agent(gui_pass, mode=mode)
        elif subcmd == "checkout":
            self._handle_assistant_checkout(rest)
        elif subcmd == "clean":
            self._handle_assistant_clean(rest)
        elif subcmd == "queue":
            self._handle_assistant_queue(rest)
        else:
            self._handle_agent(filtered, mode=mode)

    def _handle_assistant_create_and_info(self):
        """Create a new session and print ID + GUI port."""
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        DIM = get_color("DIM", "\033[2m")
        GREEN = get_color("GREEN", "\033[32m")
        RESET = get_color("RESET", "\033[0m")

        from logic._.agent.state import AgentSession, save_session
        project_root = str(self.project_root)

        session = AgentSession(
            tool_name=self.tool_name,
            codebase_root=str(self.tool_dir),
            tier=2,
        )
        save_session(session, project_root, tool_dir=str(self.tool_dir))
        self._save_active_session_id(session.id)

        from logic._.agent.command import _find_running_gui_port
        port = _find_running_gui_port()

        print(f"  {BOLD}{GREEN}Created.{RESET} {DIM}Session: {session.id}{RESET}")
        if port:
            print(f"  {DIM}GUI: http://localhost:{port}{RESET}")
            print(f"  {DIM}Port: {port}{RESET}")
        else:
            print(f"  {DIM}No GUI server running. Use --assistant --gui to start one.{RESET}")

    def _handle_assistant_checkout(self, args):
        """Switch the current tool's active session or create a new one."""
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        DIM = get_color("DIM", "\033[2m")
        RESET = get_color("RESET", "\033[0m")

        from logic._.agent.state import (
            AgentSession, save_session, load_session, list_sessions,
        )
        project_root = str(self.project_root)

        td = str(self.tool_dir)
        if args:
            sid = args[0]
            session = load_session(sid, project_root, tool_dir=td)
            if session:
                self._save_active_session_id(sid)
                print(f"  {BOLD}Checked out.{RESET} {DIM}{sid} ({session.tool_name}, "
                      f"{session.message_count} msgs, mode={session.mode}){RESET}")
            else:
                print(f"  Session {sid} not found.")
        else:
            session = AgentSession(
                tool_name=self.tool_name,
                codebase_root=str(self.tool_dir),
                tier=2,
            )
            save_session(session, project_root, tool_dir=td)
            self._save_active_session_id(session.id)
            print(f"  {BOLD}New session created.{RESET} {DIM}{session.id}{RESET}")

    def _handle_assistant_clean(self, args):
        """Delete sessions: one, many, or all.

        Usage:
            --assistant clean <id1> [id2 ...]   Delete specific sessions
            --assistant clean --all              Delete ALL sessions
        """
        import shutil
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        DIM = get_color("DIM", "\033[2m")
        GREEN = get_color("GREEN", "\033[32m")
        RESET = get_color("RESET", "\033[0m")

        from logic._.agent.state import get_sessions_dir
        sessions_dir = self.project_root / "runtime" / "sessions"
        tool_sessions_dir = get_sessions_dir(
            str(self.project_root), tool_dir=str(self.tool_dir))

        def _notify_gui_delete(sid):
            """Notify running GUI server to delete a session."""
            try:
                from logic._.agent.command import _find_running_gui_port
                import json, urllib.request
                port = _find_running_gui_port()
                if port:
                    req = urllib.request.Request(
                        f"http://localhost:{port}/api/delete",
                        data=json.dumps({"session_id": sid}).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    urllib.request.urlopen(req, timeout=2)
            except Exception:
                pass

        if "--all" in args:
            count = 0
            gui_sids = set()
            for d in (sessions_dir, tool_sessions_dir):
                if d.is_dir():
                    for item in list(d.iterdir()):
                        try:
                            gui_sids.add(item.stem if item.is_file() else item.name)
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                            count += 1
                        except OSError:
                            pass
            for sid in gui_sids:
                _notify_gui_delete(sid)
            print(f"  {BOLD}{GREEN}Cleaned.{RESET} {DIM}{count} sessions removed.{RESET}")
            return

        if not args:
            print(f"Usage: --assistant clean <id1> [id2 ...] | --assistant clean --all")
            return

        removed = 0
        for sid in args:
            found = False
            if sessions_dir.is_dir():
                for item in sessions_dir.iterdir():
                    if item.name.startswith(sid):
                        try:
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                            found = True
                            removed += 1
                        except OSError:
                            pass
            if tool_sessions_dir.is_dir():
                for item in tool_sessions_dir.iterdir():
                    if item.name.startswith(sid):
                        try:
                            item.unlink()
                            found = True
                            removed += 1
                        except OSError:
                            pass
            if found:
                _notify_gui_delete(sid)
            else:
                print(f"  {DIM}Session {sid} not found.{RESET}")
        if removed:
            print(f"  {BOLD}{GREEN}Cleaned.{RESET} {DIM}{removed} session(s) removed.{RESET}")

    def _handle_assistant_queue(self, args):
        """View or manage the task queue for a session.

        Usage:
            --assistant queue              List queued tasks
            --assistant queue clear        Clear the queue
        """
        import json
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        DIM = get_color("DIM", "\033[2m")
        RESET = get_color("RESET", "\033[0m")

        try:
            from logic._.agent.command import _find_running_gui_port
            import urllib.request
            port = _find_running_gui_port()
            if not port:
                print(f"  {BOLD}No running GUI server found.{RESET}")
                return
            base_url = f"http://localhost:{port}"

            action = args[0] if args else "list"
            req = urllib.request.Request(
                f"{base_url}/api/queue",
                data=json.dumps({"action": action}).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
            if not resp.get("ok"):
                print(f"  {BOLD}Error.{RESET} {DIM}{resp.get('error', '')}{RESET}")
                return

            if action == "list":
                queue = resp.get("queue", [])
                if not queue:
                    print(f"  {DIM}No queued tasks.{RESET}")
                else:
                    print(f"  {BOLD}Queued tasks ({len(queue)}):{RESET}")
                    for i, t in enumerate(queue, 1):
                        print(f"    {i}. {t.get('text', '')}")
            elif action == "clear":
                cleared = resp.get("cleared", 0)
                print(f"  {BOLD}Cleared.{RESET} {DIM}{cleared} task(s) removed.{RESET}")
        except Exception as e:
            print(f"  {BOLD}Error.{RESET} {DIM}{e}{RESET}")

    def _save_active_session_id(self, session_id: str):
        """Persist the active session ID for this tool."""
        import json
        config_path = self.get_data_dir() / "session.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"session_id": session_id}))

    def _get_active_session_id(self) -> str:
        """Read the active session ID for this tool, or empty string."""
        import json
        config_path = self.get_data_dir() / "session.json"
        if config_path.exists():
            try:
                return json.loads(config_path.read_text()).get("session_id", "")
            except Exception:
                pass
        return ""

    def run_setup(self):
        """Execute the tool's setup.py script using ProgressTuringMachine."""
        from logic.turing.models.progress import ProgressTuringMachine
        from logic.turing.logic import TuringStage
        from logic._.config import get_color
        
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
        from logic._.config import get_color
        
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
        from logic._.lang.utils import get_translation
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
        from logic._.config import get_color
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
        from logic._.setup.engine import ToolEngine
        
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
            from logic._.config import get_color
            RED = get_color("RED", "\033[31m")
            BOLD = get_color("BOLD", "\033[1m")
            RESET = get_color("RESET", "\033[0m")
            print(f"{BOLD}{RED}Error{RESET}: Sub-tool '{subtool_name}' ({subtool_full_name}) is not installed.")
            return False

        if not force_yes:
            from logic._.lang.utils import get_translation
            gui_logic_dir = str(self.project_root / "logic")
            confirm_msg = get_translation(gui_logic_dir, "confirm_uninstall", "Are you sure you want to uninstall '{name}'? (y/N): ", name=subtool_full_name)
            
            confirm = input(confirm_msg)
            # Erase prompt
            sys.stdout.write(f"\033[A\r\033[K")
            sys.stdout.flush()
            
            if confirm.lower() not in ['y', 'yes']:
                print(get_translation(gui_logic_dir, "uninstall_cancelled", "Uninstall cancelled."))
                return False

        from logic._.setup.engine import ToolEngine
        engine = ToolEngine(subtool_full_name, self.project_root)
        return engine.uninstall()

    def print_default_help(self):
        """Print a default help message if no parser is provided."""
        from logic._.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        RESET = get_color("RESET", "\033[0m")
        
        print(f"Usage: {self.tool_name} <command> [options]")
        print(f"\n{BOLD}Built-in commands:{RESET}")
        print(f"  setup        Run tool installation/setup")
        print(f"  install      Install a sub-tool")
        print(f"  uninstall    Uninstall a sub-tool")
        print(f"  config       Manage tool configuration")
        print(f"  skills       List and view tool skills")
        print(f"  hooks        Manage event hooks (list/enable/disable/show)")
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
