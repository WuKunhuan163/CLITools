import os
import sys
import json
import stat
import shutil


def _git_bin():
    try:
        from tool.GIT.interface.main import get_system_git
        return get_system_git()
    except ImportError:
        return _git_bin()
import subprocess
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage
from logic._.config import get_color

class ToolEngine:
    def __init__(self, tool_name, project_root, parent_tool_dir=None):
        from logic.utils import get_logic_dir
        self.tool_name = tool_name
        self.project_root = project_root
        self.tool_parent_dir = parent_tool_dir if parent_tool_dir else project_root / "tool"
        self.tool_dir = self.tool_parent_dir / tool_name
        self.tool_internal = get_logic_dir(self.tool_dir)
        self.bin_dir = project_root / "bin"
        self.registry_path = project_root / "tool.json"
        
        # Colors
        self.BOLD = get_color("BOLD", "\033[1m")
        self.GREEN = get_color("GREEN", "\033[32m")
        self.BLUE = get_color("BLUE", "\033[34m")
        self.YELLOW = get_color("YELLOW", "\033[33m")
        self.RED = get_color("RED", "\033[31m")
        self.RESET = get_color("RESET", "\033[0m")
        self.WHITE = get_color("WHITE", "\033[37m")

    def _(self, key, default, **kwargs):
        from logic._.lang.utils import get_translation
        text = get_translation(str(self.project_root / "logic"), key, default)
        return text.format(**kwargs)

    def _get_tool_bin_dir(self):
        """Returns the tool-specific bin directory: bin/<tool_name>/"""
        shortcut_name = self.tool_name
        if "." in self.tool_name:
            shortcut_name = self.tool_name.split(".")[-1]
        return self.bin_dir / shortcut_name

    def _get_shortcut_path(self):
        """Returns the path to the tool's main shortcut script."""
        shortcut_name = self.tool_name
        if "." in self.tool_name:
            shortcut_name = self.tool_name.split(".")[-1]
        tool_bin = self._get_tool_bin_dir()
        return tool_bin / shortcut_name

    def is_installed(self):
        """Check if the tool is correctly installed and operational."""
        shortcut_path = self._get_shortcut_path()

        # Check new structure: bin/<tool_name>/<shortcut_name>
        found = shortcut_path.exists() or shortcut_path.is_symlink()

        # Backward compat: check legacy flat bin/<shortcut_name>
        if not found:
            shortcut_name = self.tool_name.split(".")[-1] if "." in self.tool_name else self.tool_name
            legacy_path = self.bin_dir / shortcut_name
            found = legacy_path.exists() or legacy_path.is_symlink()

        if not (self.tool_dir.exists() and found):
            return False
        
        # Check dependencies
        tool_json_path = self.tool_dir / "tool.json"
        if tool_json_path.exists():
            try:
                with open(tool_json_path, 'r') as f:
                    tool_data = json.load(f)
                    dependencies = tool_data.get("dependencies", [])
                    for dep in dependencies:
                        dep_dir = self.tool_parent_dir / dep
                        dep_name = dep.split(".")[-1] if "." in dep else dep
                        dep_new = self.bin_dir / dep_name / dep_name
                        dep_legacy = self.bin_dir / dep_name
                        dep_found = (dep_new.exists() or dep_new.is_symlink() or
                                     dep_legacy.exists() or dep_legacy.is_symlink())
                        if not (dep_dir.exists() and dep_found):
                            return False
            except: return False
        return True

    def install(self, is_dependency=False, visited=None):
        if visited is None: visited = set()
        
        # 1. Check for circular dependency
        if self.tool_name in visited:
            return True # Already being handled
        
        visited.add(self.tool_name)

        # 2. Check if already installed
        if self.is_installed():
            try:
                from logic.git.manager import GitIgnoreManager
                gm = GitIgnoreManager(str(self.project_root))
                gm.rewrite()
            except Exception:
                pass
            if not is_dependency and os.environ.get("TOOL_QUIET") != "1":
                status = self._("label_already_installed", "Already installed")
                sys.stdout.write(f"\r\033[K{self.BOLD}{self.WHITE}{status}{self.RESET} {self.tool_name}\n")
                sys.stdout.flush()
            return True

        # 3. Check for partial installation/missing deps
        # A tool is "partial" if it has no bin shortcut but the directory exists,
        # UNLESS it's a new tool being developed (has main.py).
        shortcut_path = self._get_shortcut_path()
        has_shortcut = shortcut_path.exists() or shortcut_path.is_symlink()
        # Also check legacy location
        if not has_shortcut:
            legacy = self.bin_dir / self.tool_name
            has_shortcut = legacy.exists() or legacy.is_symlink()
        is_partial = (self.tool_dir.exists() or has_shortcut) and not self.is_installed()
        
        if self.tool_dir.exists() and (self.tool_dir / "main.py").exists() and not has_shortcut:
            is_partial = False

        tm = ProgressTuringMachine(project_root=self.project_root, tool_name=self.tool_name)
        
        # Add uninstall stage if partial
        if is_partial and not is_dependency:
            tm.add_stage(TuringStage(
                name=self.tool_name,
                action=self.uninstall_action,
                active_status=self._("label_uninstalling", "Uninstalling partial"),
                success_status=self._("label_ready", "Ready for reinstall"),
                fail_status=self._("label_failed_to_uninstall", "Failed to uninstall"),
                success_color="BOLD",
                bold_part=self._("label_uninstalling", "Uninstalling partial")
            ))

        # 1. Validation
        tm.add_stage(TuringStage(
            name=self.tool_name,
            action=self.validate_registry,
            active_status=self._("label_validating", "Validating"),
            success_status=self._("label_validated_existence", "Validated existence") + ":",
            success_name=self._("label_tool_exists_in_registry", "Tool '{name}' exists in the global registry.", name=self.tool_name),
            fail_status=self._("label_failed_to_validate", "Failed to validate"),
            success_color="BOLD",
            bold_part=self._("label_validating", "Validating")
        ))
        
        # 2. Fetching Source
        if not (self.tool_dir.exists() and (self.tool_dir / "main.py").exists()):
            tm.add_stage(TuringStage(
                name=self.tool_name,
                action=self.fetch_source,
                active_status=self._("label_fetching", "Fetching"),
                success_status=self._("label_retrieved", "Retrieved"),
                fail_status=self._("label_failed_to_fetch", "Failed to fetch"),
                success_color="BOLD",
                bold_part=self._("label_fetching", "Fetching")
            ))
        
        # 3. Tool Dependencies (Recursive)
        def handle_deps_action(stage=None):
            tool_json_path = self.tool_dir / "tool.json"
            if not tool_json_path.exists(): return True
            try:
                with open(tool_json_path, 'r') as f:
                    data = json.load(f)
                    deps = data.get("dependencies", [])
                    for dep in deps:
                        sub_engine = ToolEngine(dep, self.project_root)
                        if not sub_engine.install(is_dependency=True, visited=visited):
                            if stage: stage.error_brief = f"Failed to install dependency '{dep}'"
                            return False
                return True
            except Exception as e:
                if stage: stage.error_brief = str(e)
                return False

        tm.add_stage(TuringStage(
            name=self._("label_dependencies_for", "dependencies for {name}", name=self.tool_name),
            action=handle_deps_action,
            active_status=self._("label_installing", "Installing"),
            success_status=self._("label_ready", "Ready"),
            fail_status=self._("label_failed_to_install", "Failed to install"),
            success_color="BOLD",
            bold_part=self._("label_installing", "Installing")
        ))
        
        # 4. Pip Dependencies
        tm.add_stage(TuringStage(
            name=self._("label_pip_for", "pip dependencies for {name}", name=self.tool_name),
            action=self.handle_pip_deps,
            active_status=self._("label_installing", "Installing"),
            success_status=self._("label_installed", "Installed"),
            fail_status=self._("label_failed_to_install", "Failed to install"),
            success_color="BOLD",
            bold_part=self._("label_installing", "Installing")
        ))
        
        # 5. Entry Point
        tm.add_stage(TuringStage(
            name=self.tool_name,
            action=self.create_shortcut,
            active_status=self._("label_creating_shortcut", "Creating shortcut for"),
            success_status=self._("label_created_shortcut", "Created shortcut for"),
            fail_status=self._("label_failed_to_create_shortcut", "Failed to create shortcut for"),
            success_color="BOLD",
            bold_part=self._("label_creating_shortcut", "Creating shortcut for")
        ))
        
        # 6. Setup
        tm.add_stage(TuringStage(
            name=self._("label_the_tool_name", "the {name} tool", name=self.tool_name),
            action=self.run_setup,
            active_status=self._("label_running_setup", "Running setup"),
            success_status=self._("label_success", "Successfully"),
            fail_status=self._("label_failed_to_setup", "Failed to setup"),
            success_name=self._("label_setup_success_name", "setup {name} tool", name=self.tool_name),
            bold_part="setup"
        ))

        # Start TM
        from logic.utils import print_success_status
        self._("label_successfully_installed", "Successfully installed")
        
        # Use ephemeral=True to erase progress lines
        # Top-level tool prints success status via interface
        # Dependencies just return success/failure
        if tm.run(ephemeral=True, final_msg="", final_newline=False):
            try:
                from logic.git.manager import GitIgnoreManager
                gm = GitIgnoreManager(str(self.project_root))
                gm.rewrite()
            except Exception:
                pass
            if not is_dependency:
                from logic.utils import print_success_status
                print_success_status(f"installed {self.tool_name}")
            return True
        return False

    def uninstall(self):
        tm = ProgressTuringMachine(project_root=self.project_root, tool_name=self.tool_name)
        success_label = self._("uninstall_success_status", "Successfully uninstalled")
        final_msg = f"\r\033[K{self.BOLD}{self.GREEN}{success_label}{self.RESET} {self.tool_name}"
        
        tm.add_stage(TuringStage(
            name=self.tool_name,
            action=self.uninstall_action,
            active_status=self._("label_uninstalling", "Uninstalling"),
            success_status=success_label,
            fail_status=self._("label_failed_to_uninstall", "Failed to uninstall"),
            success_color="GREEN"
        ))
        if tm.run(ephemeral=True, final_msg=final_msg):
            return True
        return False

    def reinstall(self):
        """Force reinstall of the tool."""
        self.uninstall()
        return self.install()

    # --- Actions ---

    def validate_registry(self, stage=None):
        # If it's a subtool, we skip global registry check for now
        # or we could check the parent's metadata.
        if self.tool_parent_dir != (self.project_root / "tool"):
            return True

        if not self.registry_path.exists():
            msg = self._("registry_error", "Global tool.json not found.")
            if stage: stage.error_brief = msg
            else: print(msg)
            return False
        with open(self.registry_path, 'r') as f:
            registry = json.load(f)
            # Support both list and dict registry formats
            tools = registry.get("tools", {})
            if isinstance(tools, list):
                if self.tool_name not in tools:
                    msg = self._("tool_not_in_registry", "Tool '{name}' is not in the global registry.", name=self.tool_name)
                    if stage: stage.error_brief = msg
                    else: print(msg)
                    return False
            elif self.tool_name not in tools:
                msg = self._("tool_not_in_registry", "Tool '{name}' is not in the global registry.", name=self.tool_name)
                if stage: stage.error_brief = msg
                else: print(msg)
                return False
        
        return True

    def fetch_source(self, stage=None):
        # 0. Check if already exists locally
        if (self.tool_dir / "main.py").exists():
            return True

        rel_tool_path = self.tool_dir.relative_to(self.project_root)
        remote_source_path = rel_tool_path

        # 1. Try checkout tool/ from known branches
        sources = ["dev", "tool", "origin/tool", "origin/dev"]
        last_err = "No source found in any branch"
        for branch in sources:
            try:
                cmd = [_git_bin(), "checkout", branch, "--", str(remote_source_path)]
                res = subprocess.run(cmd, capture_output=True, cwd=str(self.project_root), text=True)
                if res.returncode == 0:
                    return True
                else:
                    last_err = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else f"Git checkout from {branch} failed"
            except Exception as e:
                last_err = str(e)

        # 2. Fallback: try resource/archived/ on tool branches
        archived_path = f"resource/archived/{self.tool_name}"
        for branch in ["tool", "origin/tool"]:
            try:
                cmd = [_git_bin(), "checkout", branch, "--", archived_path]
                res = subprocess.run(cmd, capture_output=True, cwd=str(self.project_root), text=True)
                if res.returncode == 0:
                    import shutil
                    src = self.project_root / archived_path
                    if src.exists() and (src / "main.py").exists():
                        shutil.copytree(str(src), str(self.tool_dir), dirs_exist_ok=True)
                        shutil.rmtree(str(src))
                        return True
            except Exception:
                pass

        if stage: stage.error_brief = last_err
        return False

    def handle_dependencies(self, visited=None):
        tool_json_path = self.tool_dir / "tool.json"
        if not tool_json_path.exists(): return True
        try:
            with open(tool_json_path, 'r') as f:
                data = json.load(f)
                # handle tool.json defined pip deps later, for now tool deps
                deps = data.get("dependencies", [])
                for dep in deps:
                    # Recursive install
                    sub_engine = ToolEngine(dep, self.project_root)
                    if not sub_engine.install(is_dependency=True, visited=visited): return False
            return True
        except: return False

    def _resolve_python_exec(self):
        """Resolve the managed Python executable."""
        python_tool_dir = self.project_root / "tool" / "PYTHON"
        python_exec = sys.executable
        if python_tool_dir.exists():
            from logic.utils import get_logic_dir
            utils_path = get_logic_dir(python_tool_dir) / "utils.py"
            if utils_path.exists():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("py_utils", str(utils_path))
                    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
                    python_exec = mod.get_python_exec()
                except Exception:
                    pass
        return python_exec

    def handle_pip_deps(self, stage=None):
        pip_deps = []
        optional_deps = []
        tool_json_path = self.tool_dir / "tool.json"
        if tool_json_path.exists():
            try:
                with open(tool_json_path, 'r') as f:
                    data = json.load(f)
                    pip_deps.extend(data.get("pip_dependencies", []))
                    optional_deps.extend(data.get("pip_dependencies_optional", []))
            except Exception:
                pass

        req_path = self.tool_internal / "requirements.txt"
        if not req_path.exists(): req_path = self.tool_dir / "requirements.txt"
        if req_path.exists():
            try:
                with open(req_path, 'r') as f:
                    pip_deps.extend([l.strip() for l in f if l.strip() and not l.startswith("#")])
            except Exception:
                pass

        if not pip_deps and not optional_deps:
            return True

        python_exec = self._resolve_python_exec()
        from logic.turing.display.manager import _get_configured_width, truncate_to_width
        width = _get_configured_width()

        for package in pip_deps:
            prefix = self._("label_installing_pip_dependency", "Installing pip dependency")
            msg = f"\r\033[K{self.BOLD}{self.BLUE}{prefix}{self.RESET}: {self.BOLD}{self.WHITE}{package}{self.RESET}..."
            sys.stdout.write(truncate_to_width(msg, width))
            sys.stdout.flush()

            cmd = [python_exec, "-m", "pip", "install", package]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                if stage: stage.error_brief = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else f"pip install {package} failed"
                return False

        for package in optional_deps:
            prefix = self._("label_installing_pip_dependency", "Installing pip dependency")
            suffix = self._("label_optional", "(optional)")
            msg = f"\r\033[K{self.BOLD}{self.BLUE}{prefix}{self.RESET}: {self.BOLD}{self.WHITE}{package}{self.RESET} {suffix}..."
            sys.stdout.write(truncate_to_width(msg, width))
            sys.stdout.flush()

            cmd = [python_exec, "-m", "pip", "install", package]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                skip_msg = f"\r\033[K  {self.YELLOW}Skipped{self.RESET} {package} (optional, install failed)\n"
                sys.stdout.write(skip_msg)
                sys.stdout.flush()

        return True

    def create_shortcut(self, stage=None):
        main_py = self.tool_dir / "main.py"
        if not main_py.exists():
            if stage: stage.error_brief = f"Entry point main.py not found in {self.tool_dir}"
            return False
        
        self.bin_dir.mkdir(exist_ok=True)
        
        shortcut_name = self.tool_name
        if "." in self.tool_name:
            shortcut_name = self.tool_name.split(".")[-1]

        tool_bin_dir = self._get_tool_bin_dir()
        tool_bin_dir.mkdir(exist_ok=True)

        # Clean up legacy flat shortcut if it exists
        legacy_path = self.bin_dir / shortcut_name
        if legacy_path.is_file() and not legacy_path.is_dir():
            try: os.remove(legacy_path)
            except: pass
            
        shortcut_path = tool_bin_dir / shortcut_name
        if shortcut_path.exists() or shortcut_path.is_symlink():
            try: os.remove(shortcut_path)
            except Exception as e:
                if stage: stage.error_brief = f"Failed to remove old shortcut: {e}"
                return False
        
        try:
            # Create a wrapper script that uses the managed Python
            # This ensures that tools run with their managed dependencies.
            # We use double curly braces {{}} for f-string literal braces.
            wrapper_content = f"""#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

# Resolve project root
curr = Path(__file__).resolve().parent
while curr != curr.parent:
    if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
        project_root = curr
        break
    curr = curr.parent
else:
    project_root = Path("{self.project_root}")

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Use managed python if available
python_exec = sys.executable
python_tool_dir = project_root / "tool" / "PYTHON"
if python_tool_dir.exists():
    from logic.utils import get_logic_dir
    utils_path = get_logic_dir(python_tool_dir) / "utils.py"
    if utils_path.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("py_utils", str(utils_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            python_exec = mod.get_python_exec()
        except: pass

# Run the actual tool
main_py = project_root / "{os.path.relpath(main_py, self.project_root)}"
env = os.environ.copy()
# Add project root and tool logic to PYTHONPATH
python_path = env.get('PYTHONPATH', '')
new_paths = f"{{project_root}}:{{main_py.parent}}"
env["PYTHONPATH"] = f"{{new_paths}}:{{python_path}}" if python_path else new_paths

# Distinguish tool invocation from python/pip exec passthrough
invoked_name = os.path.basename(sys.argv[0])
tool_shortcut = "{shortcut_name}"
is_tool_invocation = (invoked_name == tool_shortcut)
is_python_exec = (not is_tool_invocation and
                  invoked_name.lower() in ["python", "python3", "pip", "pip3"]
                  and "{self.tool_name}".upper() == "PYTHON")

if is_python_exec:
    if "pip" in invoked_name.lower():
        pip_path = Path(python_exec).parent / invoked_name.lower()
        if not pip_path.exists():
            pip_path = Path(python_exec).parent / "pip"
        cmd = [str(pip_path)] + sys.argv[1:]
    else:
        cmd = [python_exec] + sys.argv[1:]
else:
    cmd = [python_exec, str(main_py)] + sys.argv[1:]

# Execute the tool and preserve exit code
try:
    res = subprocess.run(cmd, env=env)
    sys.exit(res.returncode)
except KeyboardInterrupt:
    sys.exit(1)
"""
            with open(shortcut_path, 'w') as f:
                f.write(wrapper_content)
            
            # Make executable
            st = os.stat(shortcut_path)
            os.chmod(shortcut_path, st.st_mode | stat.S_IEXEC)
            
            from logic.utils import register_path
            register_path(tool_bin_dir)
            return True
        except Exception as e:
            if stage: stage.error_brief = str(e)
            return False

    def run_setup(self):
        setup_py = self.tool_dir / "setup.py"
        if not setup_py.exists(): return True
        try:
            res = subprocess.run([sys.executable, str(setup_py)], capture_output=True, text=True, cwd=str(self.project_root))
            if res.returncode != 0:
                # Clear progress line before printing captured error output
                sys.stdout.write("\r\033[K")
                if res.stdout: sys.stdout.write(res.stdout)
                if res.stderr: sys.stdout.write(res.stderr)
                sys.stdout.flush()
            return res.returncode == 0
        except Exception as e:
            sys.stdout.write(f"\r\033[KError executing setup: {e}\n")
            return False

    def uninstall_action(self):
        try:
            # Remove new-style bin/<tool_name>/ directory
            tool_bin_dir = self._get_tool_bin_dir()
            if tool_bin_dir.exists() and tool_bin_dir.is_dir():
                shutil.rmtree(tool_bin_dir)

            # Remove legacy flat shortcut if exists
            shortcut_name = self.tool_name.split(".")[-1] if "." in self.tool_name else self.tool_name
            legacy_path = self.bin_dir / shortcut_name
            if legacy_path.exists() or legacy_path.is_symlink():
                if legacy_path.is_dir():
                    shutil.rmtree(legacy_path)
                else:
                    os.remove(legacy_path)

            if self.tool_dir.exists(): shutil.rmtree(self.tool_dir)
            return not (tool_bin_dir.exists() or self.tool_dir.exists())
        except: return False
