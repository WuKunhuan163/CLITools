import os
import sys
import subprocess
from pathlib import Path
import json

class ToolBase:
    """Base class for all tools to handle dependencies and common utilities."""
    
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
            print(f"\033[1;31m错误\033[0m: 工具 '{self.tool_name}' 缺少依赖: {', '.join(missing)}")
            print(f"请运行: TOOL install {self.tool_name}")
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
        """Execute the tool's setup.py script."""
        setup_script = self.script_dir / "setup.py"
        if not setup_script.exists():
            print(f"\033[1;31m错误\033[0m: 工具 '{self.tool_name}' 没有 setup.py 脚本。")
            sys.exit(1)
        
        print(f"--- 正在执行 {self.tool_name} 的安装脚本 ---", flush=True)
        # Use current python to run setup.py
        result = subprocess.run([sys.executable, str(setup_script)] + sys.argv[2:])
        sys.exit(result.returncode)

    def get_translation(self, key, default):
        """Get tool-specific translation with fallback."""
        try:
            from proj.language_utils import get_translation
            return get_translation(str(self.script_dir / "proj"), key, default)
        except ImportError:
            return default

    def setup_gui(self):
        """Centralized GUI environment setup."""
        try:
            from proj.gui import setup_gui_environment
            setup_gui_environment()
        except ImportError:
            pass

