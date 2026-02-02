import os
import sys
import json
import stat
import shutil
import subprocess
from pathlib import Path
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage
from logic.config import get_color

class ToolEngine:
    def __init__(self, tool_name, project_root):
        from logic.utils import get_logic_dir
        self.tool_name = tool_name
        self.project_root = project_root
        self.tool_parent_dir = project_root / "tool"
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
        from logic.lang.utils import get_translation
        text = get_translation(str(self.project_root / "logic"), key, default)
        return text.format(**kwargs)

    def is_installed(self):
        """Check if the tool is correctly installed and operational."""
        link_path = self.bin_dir / self.tool_name
        if not (self.tool_dir.exists() and (link_path.exists() or link_path.is_symlink())):
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
                        dep_link = self.bin_dir / dep
                        if not (dep_dir.exists() and (dep_link.exists() or dep_link.is_symlink())):
                            return False
            except: return False
        return True

    def install(self, is_dependency=False, visited=None):
        if visited is None: visited = set()
        
        # 1. Check for circular dependency
        if self.tool_name in visited:
            # We already visited this tool in the current recursion stack
            return True # Assume it will be handled by the outer call
        
        visited.add(self.tool_name)

        # 2. Check if correctly installed
        if self.is_installed():
            status = self._("label_already_installed", "Already installed")
            msg = f"\r\033[K{self.BOLD}{self.WHITE}{status}{self.RESET} {self.tool_name}"
            if is_dependency:
                sys.stdout.write(msg)
                sys.stdout.flush()
            else:
                print(msg)
            return True

        # 3. Check for partial installation/missing deps
        is_partial = self.tool_dir.exists() or (self.bin_dir / self.tool_name).exists()
        
        tm = ProgressTuringMachine()
        
        # Add uninstall stage if partial
        if is_partial and not is_dependency:
            tm.add_stage(TuringStage(
                name=self.tool_name,
                action=self.uninstall_action,
                active_status=self._("label_uninstalling", "Uninstalling partial"),
                success_status=self._("label_ready", "Ready for reinstall"),
                success_color="BOLD"
            ))

        # 1. Validation
        tm.add_stage(TuringStage(
            name=self._("label_the_existence_of_tool", "the existence of tool '{name}' in global registry", name=self.tool_name),
            action=self.validate_registry,
            active_status=self._("label_validating", "Validating"),
            success_status=self._("label_passed", "Passed"),
            success_color="BOLD"
        ))
        
        # 2. Fetching Source
        if not (self.tool_dir.exists() and (self.tool_dir / "main.py").exists()):
            tm.add_stage(TuringStage(
                name=self.tool_name,
                action=self.fetch_source,
                active_status=self._("label_fetching", "Fetching"),
                success_status=self._("label_retrieved", "Retrieved"),
                success_color="BOLD",
                is_sticky=True
            ))
        
        # 3. Tool Dependencies (Recursive)
        def handle_deps_action():
            return self.handle_dependencies(visited=visited)

        tm.add_stage(TuringStage(
            name=self._("label_dependencies_for", "dependencies for {name}", name=self.tool_name),
            action=handle_deps_action,
            active_status=self._("label_installing", "Installing"),
            success_status=self._("label_ready", "Ready"),
            success_color="BOLD"
        ))
        
        # 4. Pip Dependencies
        tm.add_stage(TuringStage(
            name=self._("label_pip_for", "pip dependencies for {name}", name=self.tool_name),
            action=self.handle_pip_deps,
            active_status=self._("label_installing", "Installing"),
            success_status=self._("label_installed", "Installed"),
            success_color="BOLD"
        ))
        
        # 5. Entry Point
        tm.add_stage(TuringStage(
            name=self.tool_name,
            action=self.create_shortcut,
            active_status=self._("label_creating_shortcut", "Creating shortcut for"),
            success_status=self._("label_created_shortcut", "Created shortcut for"),
            success_color="BOLD"
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

        # IMPORTANT: Run TM. Only if successful we show the final GREEN Success message.
        success_label = self._("label_successfully_installed", "Successfully installed")
        final_msg = f"\r\033[K{self.BOLD}{self.GREEN}{success_label}{self.RESET} {self.tool_name}"
        
        if is_dependency:
            # If it's a dependency, we want its final success message to be erasable by the parent
            # So we pass final_newline=False
            if tm.run(ephemeral=True, final_msg=final_msg, final_newline=False):
                return True
        else:
            if tm.run(ephemeral=True, final_msg=final_msg):
                print("") # Final newline for top-level tool
                return True
        return False

    def uninstall(self):
        tm = ProgressTuringMachine()
        success_label = self._("uninstall_success_status", "Successfully uninstalled")
        final_msg = f"\r\033[K{self.BOLD}{self.GREEN}{success_label}{self.RESET} {self.tool_name}"
        
        tm.add_stage(TuringStage(
            name=self.tool_name,
            action=self.uninstall_action,
            active_status=self._("label_uninstalling", "Uninstalling"),
            success_status=success_label,
            success_color="GREEN"
        ))
        if tm.run(ephemeral=True, final_msg=final_msg):
            print("")
            return True
        return False

    def reinstall(self):
        """Force reinstall of the tool."""
        self.uninstall()
        return self.install()

    # --- Actions ---

    def validate_registry(self):
        if not self.registry_path.exists():
            print(self._("registry_error", "Global tool.json not found."))
            return False
        with open(self.registry_path, 'r') as f:
            registry = json.load(f)
            # Support both list and dict registry formats
            tools = registry.get("tools", {})
            if isinstance(tools, list):
                if self.tool_name not in tools:
                    print(self._("tool_not_in_registry", "Tool '{name}' is not in the global registry.", name=self.tool_name))
                    return False
            elif self.tool_name not in tools:
                print(self._("tool_not_in_registry", "Tool '{name}' is not in the global registry.", name=self.tool_name))
                return False
        
        # Print specific success message as requested
        # Format: <Validated existence:><Tool TOOL_NAME exists in the global registry.>
        validated_label = self._("label_validated_existence", "Validated existence")
        tool_exists_msg = self._("tool_exists_in_registry", "Tool {name} exists in the global registry.", name=self.tool_name)
        sys.stdout.write(f"\r\033[K{self.BOLD}{self.WHITE}{validated_label}{RESET}: {tool_exists_msg}\n")
        sys.stdout.flush()
        return True

    def fetch_source(self):
        # Try local branch first, then remote
        sources = ["tool", "origin/tool"]
        for branch in sources:
            try:
                cmd = ["git", "checkout", branch, "--", f"tool/{self.tool_name}"]
                if subprocess.run(cmd, capture_output=True, cwd=str(self.project_root)).returncode == 0:
                    return True
            except: pass
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

    def handle_pip_deps(self):
        # Merge requirements.txt and tool.json pip_dependencies
        pip_deps = []
        tool_json_path = self.tool_dir / "tool.json"
        if tool_json_path.exists():
            try:
                with open(tool_json_path, 'r') as f:
                    pip_deps.extend(json.load(f).get("pip_dependencies", []))
            except: pass
            
        req_path = self.tool_internal / "requirements.txt"
        if not req_path.exists(): req_path = self.tool_dir / "requirements.txt"
        if req_path.exists():
            try:
                with open(req_path, 'r') as f:
                    pip_deps.extend([l.strip() for l in f if l.strip() and not l.startswith("#")])
            except: pass
            
        if not pip_deps: return True
        
        # Resolve python
        python_tool_dir = self.project_root / "tool" / "PYTHON"
        if not python_tool_dir.exists():
            # If PYTHON is in dependencies, it will be installed in handle_dependencies.
            return True 
        
        from logic.utils import get_logic_dir
        utils_path = get_logic_dir(python_tool_dir) / "utils.py"
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("py_utils", str(utils_path))
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            python_exec = mod.get_python_exec()
            
            for package in pip_deps:
                # Update status message for each package
                status = self._("label_installing_pip_package", "Installing pip dependency: {package}...", package=package)
                sys.stdout.write(f"\r\033[K{self.BOLD}{self.BLUE}{status}{self.RESET}")
                sys.stdout.flush()
                
                cmd = [python_exec, "-m", "pip", "install", package]
                if subprocess.run(cmd, capture_output=True).returncode != 0:
                    return False
            return True
        except: return False

    def create_shortcut(self):
        main_py = self.tool_dir / "main.py"
        if not main_py.exists(): return False
        
        self.bin_dir.mkdir(exist_ok=True)
        link_path = self.bin_dir / self.tool_name
        if link_path.exists() or link_path.is_symlink(): os.remove(link_path)
        
        try:
            st = os.stat(main_py); os.chmod(main_py, st.st_mode | stat.S_IEXEC)
            
            # Pure symlink - re-execution logic is now inside ToolBase
            os.symlink(main_py, link_path)
            
            from main import register_path
            register_path(self.bin_dir)
            return True
        except: return False

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
            link_path = self.bin_dir / self.tool_name
            if link_path.exists() or link_path.is_symlink(): os.remove(link_path)
            if self.tool_dir.exists(): shutil.rmtree(self.tool_dir)
            return not (link_path.exists() or self.tool_dir.exists())
        except: return False
