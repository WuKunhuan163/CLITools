import os
import sys
import subprocess
import shutil
import json
import re
from pathlib import Path
from typing import Optional, Callable

from logic.config import get_color
from logic.utils import get_logic_dir
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage

def dev_sync(project_root: Path, quiet: bool = False, translation_func: Optional[Callable] = None) -> bool:
    """Synchronize branches in a linear chain: dev -> tool -> main -> test."""
    from logic.git.utils import align_branches_logic
    from logic.git.persistence import get_persistence_manager
    
    pm = get_persistence_manager(project_root)
    locker_key = pm.save_tools_persistence()
    try:
        return align_branches_logic(project_root, quiet=quiet, translation_func=translation_func)
    finally:
        if locker_key:
            pm.restore(locker_key)

def dev_reset(project_root: Path, shared_logic_dir: Path, translation_func: Optional[Callable] = None):
    """Reset main and test branches to a clean state using templates."""
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    try:
        current = subprocess.check_output(["/usr/bin/git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=str(project_root)).strip()
        if current != "tool":
            warning_label = _("label_warning", "Warning")
            print(f"{BOLD}{YELLOW}{warning_label}{RESET}: " + _("reset_warning_branch", "Reset is recommended from 'tool' branch."))
            
        subprocess.run(["/usr/bin/git", "checkout", "main"], cwd=str(project_root), check=True)
        
        init_dir = shared_logic_dir / "init"
        if (init_dir / ".gitignore").exists():
            shutil.copy(init_dir / ".gitignore", project_root / ".gitignore")
        if (init_dir / ".gitattributes").exists():
            shutil.copy(init_dir / ".gitattributes", project_root / ".gitattributes")
            
        subprocess.run(["/usr/bin/git", "add", ".gitignore", ".gitattributes"], cwd=str(project_root), check=True)
        subprocess.run(["/usr/bin/git", "commit", "-m", "Reset main branch to template state"], cwd=str(project_root), capture_output=True)
        
        subprocess.run(["/usr/bin/git", "clean", "-fd"], cwd=str(project_root), stderr=subprocess.DEVNULL)
        for d in ["data", "tmp", "tool", "resource"]:
            p = project_root / d
            if p.exists() and p.is_dir():
                shutil.rmtree(p)
                subprocess.run(["/usr/bin/git", "rm", "-rf", "--cached", d], stderr=subprocess.DEVNULL, cwd=str(project_root))
        
        subprocess.run(["/usr/bin/git", "commit", "--amend", "--no-edit"], cwd=str(project_root), capture_output=True)
        subprocess.run(["/usr/bin/git", "branch", "-D", "test"], stderr=subprocess.DEVNULL, cwd=str(project_root))
        subprocess.run(["/usr/bin/git", "checkout", "-b", "test"], cwd=str(project_root), check=True)
        subprocess.run(["/usr/bin/git", "checkout", current], cwd=str(project_root), check=True)
        
        success_status = _("label_success", "Successfully")
        print(f"{BOLD}{GREEN}{success_status} reset{RESET} main and test branches.")
    except Exception as e:
        error_label = _("label_error", "Error")
        print(f"{BOLD}{RED}{error_label}{RESET}: " + _("reset_failed", "Reset failed: {error}", error=str(e)))

def dev_enter(branch: str, project_root: Path, force: bool = False, translation_func: Optional[Callable] = None):
    """Switch to main or test branch safely."""
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    try:
        if force:
            print(f"{BOLD}{BLUE}Force switching to {branch} branch...{RESET}")
            subprocess.run(["/usr/bin/git", "checkout", "-f", branch], cwd=str(project_root), check=True)
            subprocess.run(["/usr/bin/git", "clean", "-fdx", "--exclude=tool/*/data/", "--exclude=data/"], cwd=str(project_root), check=True)
        else:
            # Auto-commit local changes if any
            status = subprocess.check_output(["/usr/bin/git", "status", "--porcelain"], text=True, cwd=str(project_root))
            if status:
                auto_commit_label = _("label_auto_committing", "Auto-committing")
                print(f"{BOLD}{BLUE}{auto_commit_label}{RESET} local changes before switching...")
                subprocess.run(["/usr/bin/git", "add", "-A"], check=True, cwd=str(project_root))
                subprocess.run(["/usr/bin/git", "commit", "-m", f"Auto-commit before entering {branch}"], check=True, cwd=str(project_root), capture_output=True)
            
            subprocess.run(["/usr/bin/git", "checkout", branch], cwd=str(project_root), check=True)
            # Always clean when entering test/main to remove leftover ignored files
            subprocess.run(["/usr/bin/git", "clean", "-fdx", "--exclude=tool/*/data/", "--exclude=data/"], cwd=str(project_root), check=True)
    except Exception as e:
        error_label = _("label_error", "Error")
        print(f"{BOLD}{RED}{error_label}{RESET}: {e}")

def dev_create(tool_name: str, project_root: Path, translation_func: Optional[Callable] = None):
    """Create a new tool template."""
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    tool_dir = project_root / "tool" / tool_name
    
    # Get current branch
    try:
        current_branch = subprocess.check_output(["/usr/bin/git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=str(project_root)).strip()
    except:
        current_branch = "dev"

    is_dev_branch = current_branch in ["dev", "tool"] or current_branch.startswith("feature/")
    
    from tool.GIT.interface.main import run_git_tool_managed
    
    if not is_dev_branch:
        # Auto-commit local changes before checkout to avoid errors
        try:
            status_res = run_git_tool_managed(["status", "--porcelain"], cwd=str(project_root))
            if status_res.stdout.strip():
                # Erasable message
                msg = f"{BOLD}{BLUE}Auto-committing{RESET} local changes before switching branch..."
                sys.stdout.write(msg)
                sys.stdout.flush()
                
                run_git_tool_managed(["add", "."], cwd=str(project_root))
                run_git_tool_managed(["commit", "-m", "Auto-commit before dev create"], cwd=str(project_root))
                
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
        except: pass

        try:
            msg = f"{BOLD}{BLUE}Switching to git branch{RESET} 'dev' for development..."
            sys.stdout.write(msg)
            sys.stdout.flush()
            
            run_git_tool_managed(["checkout", "dev"], cwd=str(project_root))
            current_branch = "dev"
            
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
        except: pass
    
    if tool_dir.exists():
        print(f"{BOLD}{RED}Error{RESET}: Tool '{tool_name}' already exists.")
        return
    
    tool_dir.mkdir(parents=True)
    (tool_dir / "report").mkdir(exist_ok=True)
    (tool_dir / "test").mkdir(exist_ok=True)
    tool_internal = get_logic_dir(tool_dir)
    tool_internal.mkdir()
    (tool_internal / "translation").mkdir(parents=True)
    (tool_dir / "interface").mkdir(exist_ok=True)
    (tool_dir / "hooks" / "interface").mkdir(parents=True, exist_ok=True)
    (tool_dir / "hooks" / "instance").mkdir(parents=True, exist_ok=True)
    
    main_content = f'''#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Universal path resolver bootstrap
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from logic.config import get_color

def main():
    tool = ToolBase("{tool_name}")
    
    parser = argparse.ArgumentParser(description="Tool {tool_name}", add_help=False)
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    if args.demo:
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        
        import time
        from logic.turing.display.manager import _get_configured_width, truncate_to_width
        width = _get_configured_width()
        
        for i in range(3, 0, -1):
            msg = f"\\r\\033[K{{BOLD}}{{BLUE}}Progressing{{RESET}}... {{i}}s"
            sys.stdout.write(truncate_to_width(msg, width))
            sys.stdout.flush()
            time.sleep(1)
            
        msg = f"\\r\\033[K{{BOLD}}{{GREEN}}Successfully{{RESET}} finished!\\n"
        sys.stdout.write(truncate_to_width(msg, width))
        sys.stdout.flush()
        return

    print("Hello World!")

if __name__ == "__main__":
    main()
'''
    with open(tool_dir / "main.py", 'w') as f: f.write(main_content)
    os.chmod(tool_dir / "main.py", 0o755)
    
    setup_content = f'''#!/usr/bin/env python3
import sys
from pathlib import Path

# Universal path resolver bootstrap
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.setup.engine import ToolEngine
from logic.utils import print_success_status

def setup():
    tool_name = "{tool_name}"
    engine = ToolEngine(tool_name, project_root)
    
    # 1. Standard installation (dependencies + shortcut)
    return engine.install()

if __name__ == "__main__":
    setup()
'''
    with open(tool_dir / "setup.py", 'w') as f: f.write(setup_content)
    
    tool_json = {
        "name": tool_name,
        "version": "1.0.0",
        "description": f"Template tool {tool_name}",
        "purpose": "Showcase tool development guidelines",
        "dependencies": ["PYTHON"]
    }
    with open(tool_dir / "tool.json", 'w') as f: json.dump(tool_json, f, indent=2)
    
    short_name = tool_name.split('.')[-1] if '.' in tool_name else tool_name
    
    # Update global tool.json
    registry_path = project_root / "tool.json"
    if registry_path.exists():
        try:
            with open(registry_path, 'r') as f: registry = json.load(f)
            if "tools" not in registry: registry["tools"] = {}
            if tool_name not in registry["tools"]:
                registry["tools"][tool_name] = {
                    "description": tool_json["description"],
                    "purpose": tool_json["purpose"]
                }
                with open(registry_path, 'w') as f: json.dump(registry, f, indent=2)
        except: pass
    
    zh_trans = {"hello": "你好, 世界!"}
    with open(tool_internal / "translation" / "zh.json", 'w') as f: json.dump(zh_trans, f, indent=2)
    
    test_help_content = f'''import unittest
import subprocess
import sys
from pathlib import Path

class TestHelp(unittest.TestCase):
    def test_help(self):
        """Test that the tool supports --help and returns success."""
        project_root = Path(__file__).resolve().parent.parent.parent
        bin_path = project_root / "bin" / "{tool_name.split('.')[-1] if '.' in tool_name else tool_name}"
        if not bin_path.exists():
            bin_path = project_root / "tool" / "{tool_name}" / "main.py"
            
        cmd = [sys.executable, str(bin_path), "--help"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Help command failed with code {{res.returncode}}: {{res.stderr}}")
        self.assertIn("usage:", res.stdout.lower() or res.stderr.lower())

if __name__ == "__main__":
    unittest.main()
'''
    with open(tool_dir / "test" / "test_00_help.py", 'w') as f: f.write(test_help_content)

    test_basic_content = f'''import unittest
import subprocess
import sys
from pathlib import Path

EXPECTED_TIMEOUT = 30

class TestBasic(unittest.TestCase):
    def test_no_args(self):
        """Test that the tool handles no arguments gracefully."""
        project_root = Path(__file__).resolve().parent.parent.parent
        bin_path = project_root / "bin" / "{tool_name.split('.')[-1] if '.' in tool_name else tool_name}"
        if not bin_path.exists():
            bin_path = project_root / "tool" / "{tool_name}" / "main.py"

        cmd = [sys.executable, str(bin_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        # Should exit 0 (help) or 1 (error) but not crash
        self.assertIn(res.returncode, [0, 1],
            f"Unexpected exit code {{res.returncode}}: {{res.stderr}}")

if __name__ == "__main__":
    unittest.main()
'''
    with open(tool_dir / "test" / "test_01_basic.py", 'w') as f: f.write(test_basic_content)

    # --- Interface template ---
    interface_content = f'''"""
{tool_name} Tool Interface

Provides functions for cross-tool communication.
Other tools can access this via:
    from interface import get_interface
    iface = get_interface("{tool_name}")
"""


def get_info():
    """Return basic tool info dict."""
    return {{"name": "{tool_name}", "version": "1.0.0"}}
'''
    with open(tool_dir / "interface" / "main.py", 'w') as f: f.write(interface_content)

    # --- Hooks: template interface ---
    hook_iface_content = f'''"""Hook interface: on_demo_action

Fired when the tool's --demo command runs.

kwargs:
    tool: ToolBase instance
    countdown: int (current countdown value)
"""
from logic.tool.hooks.engine import HookInterface


class OnDemoAction(HookInterface):
    event_name = "on_demo_action"
    description = "Fired during --demo countdown. Extend to add custom logic."
'''
    with open(tool_dir / "hooks" / "interface" / "on_demo_action.py", 'w') as f: f.write(hook_iface_content)

    # --- Hooks: template instance ---
    hook_inst_content = f'''"""Hook instance: demo_logger

Logs each demo countdown tick to the session log.

Event: on_demo_action
"""
from logic.tool.hooks.engine import HookInstance


class DemoLogger(HookInstance):
    name = "demo_logger"
    description = "Log demo countdown ticks to the session log."
    event_name = "on_demo_action"
    enabled_by_default = False

    def execute(self, **kwargs):
        tool = kwargs.get("tool")
        countdown = kwargs.get("countdown", 0)
        if tool:
            tool.log(f"Demo countdown: {{countdown}}")
        return {{"logged": True, "countdown": countdown}}
'''
    with open(tool_dir / "hooks" / "instance" / "demo_logger.py", 'w') as f: f.write(hook_inst_content)

    # --- Hooks config ---
    hooks_config = {{"enabled": [], "disabled": []}}
    with open(tool_dir / "hooks" / "config.json", 'w') as f: json.dump(hooks_config, f, indent=2)

    # --- for_agent.md ---
    for_agent_content = f"""# {tool_name} — Agent Quick Reference

## CLI Commands

| Command | Description |
|---------|-------------|
| `{short_name} --demo` | Run demo countdown |
| `{short_name} setup` | Run tool setup |
| `{short_name} hooks list` | List available hooks |
| `{short_name} hooks enable <name>` | Enable a hook instance |
| `{short_name} hooks disable <name>` | Disable a hook instance |
| `{short_name} skills list` | List tool skills |

## Hooks

This tool supports the hooks system. See `{short_name} hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("{tool_name}")
info = iface.get_info()
```
"""
    with open(tool_dir / "for_agent.md", 'w') as f: f.write(for_agent_content)

    # --- Enhanced README ---
    readme_content = f"""# {tool_name}

{tool_name} tool template.

## Quick Start

```bash
{short_name} --demo         # Run demo
{short_name} setup          # Install dependencies
{short_name} --help         # Show help
```

## Hooks

Event-driven callback system. See [Hooks Documentation](#hooks-system).

```bash
{short_name} hooks list                  # List events and instances
{short_name} hooks enable demo_logger    # Enable the demo logger hook
{short_name} hooks disable demo_logger   # Disable it
{short_name} hooks show demo_logger      # Inspect a hook instance
```

### Hook Events

| Event | Description |
|-------|-------------|
| `on_tool_start` | Fired when the tool begins execution (base) |
| `on_tool_exit` | Fired when the tool finishes execution (base) |
| `on_demo_action` | Fired during --demo countdown |

### Hook Instances

| Instance | Event | Default |
|----------|-------|---------|
| `demo_logger` | `on_demo_action` | disabled |

## Interface

```python
from interface import get_interface
iface = get_interface("{tool_name}")
info = iface.get_info()  # {{"name": "{tool_name}", "version": "1.0.0"}}
```

## Skills

```bash
{short_name} skills list
{short_name} skills show <name>
{short_name} skills search <query>
```

## Testing

```bash
TOOL test {tool_name}
```
"""
    with open(tool_dir / "README.md", 'w') as f: f.write(readme_content)

    try:
        res = run_git_tool_managed(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(project_root))
        current_real = res.stdout.strip() if res.returncode == 0 else "dev"
        run_git_tool_managed(["add", "."], cwd=str(project_root))
        run_git_tool_managed(["commit", "-m", f"Create tool template for {tool_name}"], cwd=str(project_root))
        
        msg = f"{BOLD}{BLUE}Pushing to remote{RESET} branch '{current_real}'..."
        sys.stdout.write(msg)
        sys.stdout.flush()
        run_git_tool_managed(["push", "origin", f"HEAD:{current_real}", "--force"], cwd=str(project_root))
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
    except: pass

    success_status = _("label_success", "Successfully")
    print(f"{BOLD}{GREEN}{success_status}{RESET} " + _("created_tool_template", "created tool template at {name}", name=tool_dir))

def dev_sanity_check(tool_name: str, project_root: Path, fix: bool = False, translation_func: Optional[Callable] = None) -> bool:
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    tool_dir = project_root / "tool" / tool_name
    if not tool_dir.exists():
        print(f"Error: Tool '{tool_name}' not found.")
        return False
    
    reqs = {
        "files": ["main.py", "setup.py", "tool.json", "README.md"],
        "dirs": ["logic", "logic/translation", "test"]
    }
    missing = []
    for f in reqs["files"]:
        if not (tool_dir / f).exists(): missing.append(f)
    for d in reqs["dirs"]:
        if not (tool_dir / d).exists(): missing.append(d)
    
    if fix and missing:
        # ... fix logic (from main.py) ...
        if "logic" in missing:
            get_logic_dir(tool_dir).mkdir(exist_ok=True)
            print(_("fixed_created_logic", "Fixed: Created logic/ directory for '{name}'", name=tool_name))
            missing.remove("logic")
        
        if "logic/translation" in missing:
            tool_internal = get_logic_dir(tool_dir)
            trans_json = tool_internal / "translation.json"
            trans_dir = tool_internal / "translation"
            if trans_json.exists():
                trans_dir.mkdir(parents=True, exist_ok=True)
                try:
                    with open(trans_json, 'r') as f:
                        data = json.load(f)
                        for lang, items in data.items():
                            with open(trans_dir / f"{lang}.json", 'w') as lf:
                                json.dump(items, lf, indent=2)
                    print(_("fixed_converted_translation", "Fixed: Converted logic/translation.json to logic/translation/ directory for '{name}'", name=tool_name))
                    missing.remove("logic/translation")
                except Exception as e:
                    print(f"Error fixing translation: {e}")
            else:
                trans_dir.mkdir(parents=True, exist_ok=True)
                print(_("fixed_created_logic_trans", "Fixed: Created empty logic/translation/ directory for '{name}'", name=tool_name))
                missing.remove("logic/translation")
        
        for f in list(missing):
            if f == "README.md":
                with open(tool_dir / "README.md", 'w') as f_out:
                    f_out.write(f"# {tool_name}\n\n{tool_name} tool.")
                print(_("fixed_created_readme", "Fixed: Created basic README.md for '{name}'", name=tool_name))
                missing.remove("README.md")
            elif f == "tool.json":
                reg_path = project_root / "tool.json"
                info = {}
                if reg_path.exists():
                    with open(reg_path, 'r') as f_reg:
                        info = json.load(f_reg).get("tools", {}).get(tool_name, {})
                minimal_tool_json = {
                    "name": tool_name,
                    "version": "1.0.0",
                    "description": info.get("description", f"Tool {tool_name}"),
                    "purpose": info.get("purpose", ""),
                    "dependencies": []
                }
                with open(tool_dir / "tool.json", 'w') as f_out:
                    json.dump(minimal_tool_json, f_out, indent=2)
                print(_("fixed_created_tool_json", "Fixed: Created minimal tool.json for '{name}'", name=tool_name))
                missing.remove("tool.json")
            elif f == "test":
                (tool_dir / "test").mkdir(exist_ok=True)
                print(f"Fixed: Created test/ directory for '{tool_name}'")
                missing.remove("test")

    if missing:
        fail_label = _("sanity_failed", "Sanity check failed")
        print(f"{BOLD}{RED}{fail_label}{RESET} for '{tool_name}': Missing {', '.join(missing)}")
        return False
    
    pass_label = _("sanity_passed", "Sanity check passed")
    print(f"{BOLD}{GREEN}{pass_label}{RESET} for '{tool_name}'.")
    return True

def dev_audit_test(tool_name: str, project_root: Path, fix: bool = False) -> bool:
    """Audit unit test naming conventions."""
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    actual_tool_name = "root" if tool_name in ["root", "TOOL"] else tool_name
    test_dir = project_root / "test" if actual_tool_name == "root" else project_root / "tool" / actual_tool_name / "test"
    
    if not test_dir.exists():
        print(f"No test directory found for {tool_name}")
        return True

    tests = sorted([f for f in test_dir.glob("test_*.py")])
    if not tests:
        print(f"No tests found for {tool_name}")
        return True

    violations = []
    seen_indices = {}
    
    for test_file in tests:
        name = test_file.name
        match = re.match(r"test_(\d+)_", name)
        if not match:
            violations.append((test_file, "Missing index (e.g. test_00_...)"))
            continue
            
        index = match.group(1)
        if index in seen_indices:
            violations.append((test_file, f"Duplicate index {index} (already used by {seen_indices[index]})"))
        else:
            seen_indices[index] = name

    if "00" in seen_indices and "help" not in seen_indices["00"].lower():
        violations.append((test_dir / seen_indices["00"], "Index 00 should be reserved for help test"))

    if not violations:
        print(f"{BOLD}{GREEN}Audit passed{RESET} for {tool_name} tests.")
        return True

    print(f"{BOLD}{RED}Found violations in {tool_name} tests:{RESET}")
    for test_file, reason in violations:
        print(f"  {test_file.name}: {reason}")
        if fix:
            if "Index 00 should be reserved" in reason:
                idx = 1
                while f"{idx:02d}" in seen_indices: idx += 1
                new_index = f"{idx:02d}"
                new_name = test_file.name.replace("test_00_", f"test_{new_index}_")
                test_file.rename(test_file.parent / new_name)
                print(f"    {BOLD}{GREEN}Fixed{RESET}: Renamed to {new_name}")
            elif "Missing index" in reason:
                idx = 0
                while f"{idx:02d}" in seen_indices: idx += 1
                new_index = f"{idx:02d}"
                new_name = f"test_{new_index}_{test_file.name[5:]}"
                test_file.rename(test_file.parent / new_name)
                print(f"    {BOLD}{GREEN}Fixed{RESET}: Renamed to {new_name}")
    
    return False

def dev_audit_archived(project_root: Path) -> bool:
    """Audit for duplicate tools between tool/ and resource/archived/ on the tool branch."""
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    tool_dir = project_root / "tool"
    archived_dir = project_root / "resource" / "archived"

    active_tools = set()
    if tool_dir.exists():
        for d in tool_dir.iterdir():
            if d.is_dir() and (d / "main.py").exists():
                active_tools.add(d.name)

    archived_tools = set()
    if archived_dir.exists():
        for d in archived_dir.iterdir():
            if d.is_dir() and (d / "main.py").exists():
                archived_tools.add(d.name)

    duplicates = active_tools & archived_tools
    if duplicates:
        print(f"{BOLD}{RED}Found duplicate tools{RESET} in both tool/ and resource/archived/:")
        for name in sorted(duplicates):
            print(f"  {name}")
        return False

    total = len(active_tools) + len(archived_tools)
    print(f"{BOLD}{GREEN}No duplicates{RESET}: {len(active_tools)} active, {len(archived_tools)} archived tools.")
    return True


def dev_audit_bin(project_root: Path, fix: bool = False) -> bool:
    """Audit bin/ directory for the tool-subdirectory structure (bin/<tool>/<tool>)."""
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    bin_dir = project_root / "bin"
    if not bin_dir.exists():
        print(f"{BOLD}{YELLOW}Warning{RESET}: bin/ directory not found.")
        return True
    
    registry_path = project_root / "tool.json"
    tools = []
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            data = json.load(f)
            tools_data = data.get("tools", [])
            if isinstance(tools_data, dict): tools = list(tools_data.keys())
            elif isinstance(tools_data, list): tools = tools_data
    
    def _is_valid_bootstrap(filepath):
        try:
            with open(filepath, 'r') as f_in:
                content = f_in.read()
                return "# Use managed python if available" in content and "subprocess.run" in content
        except:
            return False

    violations = []

    # Check for legacy flat shortcuts (files directly in bin/ that aren't TOOL)
    for f in bin_dir.iterdir():
        if f.name == "TOOL": continue
        if f.is_file() and not f.is_symlink():
            shortcut_name = f.name
            matched_tool = None
            for t in tools:
                sn = t.split(".")[-1] if "." in t else t
                if sn == shortcut_name:
                    matched_tool = t
                    break
            if matched_tool:
                violations.append((shortcut_name, matched_tool, "Legacy flat shortcut (should be in bin/{}/{}/)".format(shortcut_name, shortcut_name)))

    # Check each tool has proper bin/<tool>/<tool> structure
    for t in tools:
        shortcut_name = t.split(".")[-1] if "." in t else t
        if shortcut_name == "TOOL": continue
        tool_src_dir = project_root / "tool" / t
        if not tool_src_dir.exists():
            continue

        tool_bin_dir = bin_dir / shortcut_name
        main_shortcut = tool_bin_dir / shortcut_name

        if not tool_bin_dir.exists() or not tool_bin_dir.is_dir():
            violations.append((shortcut_name, t, "Missing bin/{sn}/ directory".format(sn=shortcut_name)))
        elif not (main_shortcut.exists() or main_shortcut.is_symlink()):
            violations.append((shortcut_name, t, "Missing bin/{sn}/{sn} shortcut".format(sn=shortcut_name)))
        elif main_shortcut.is_file() and not main_shortcut.is_symlink() and not _is_valid_bootstrap(main_shortcut):
            violations.append((shortcut_name, t, "Invalid bootstrap script in bin/{sn}/{sn}".format(sn=shortcut_name)))

    if not violations:
        print(f"{BOLD}{GREEN}Success{RESET}: All tool shortcuts use the bin/<tool>/ directory structure.")
        return True
    
    print(f"{BOLD}{RED}Found shortcut violations in bin/{RESET}:")
    for shortcut_name, tool_name, reason in violations:
        print(f"  {shortcut_name} ({reason})")
        if fix:
            # Remove legacy flat shortcut if present
            legacy = bin_dir / shortcut_name
            if legacy.is_file() and not legacy.is_dir():
                try:
                    os.remove(legacy)
                    print(f"    {BOLD}{YELLOW}Removed{RESET}: legacy flat shortcut bin/{shortcut_name}")
                except: pass

            from logic.tool.setup.engine import ToolEngine
            engine = ToolEngine(tool_name, project_root)
            if engine.create_shortcut():
                print(f"    {BOLD}{GREEN}Fixed{RESET}: Created bin/{shortcut_name}/{shortcut_name} bootstrap script.")
            else:
                print(f"    {BOLD}{RED}Failed to fix{RESET}: could not create shortcut.")
                
    return False


def dev_migrate_bin(project_root: Path) -> bool:
    """Migrate flat bin/ shortcuts to the new bin/<tool>/ directory structure."""
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    YELLOW = get_color("YELLOW", "\033[33m")
    BLUE = get_color("BLUE", "\033[34m")
    RESET = get_color("RESET", "\033[0m")

    bin_dir = project_root / "bin"
    if not bin_dir.exists():
        print(f"{BOLD}{YELLOW}Warning{RESET}: bin/ directory not found.")
        return True

    registry_path = project_root / "tool.json"
    tools = []
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            data = json.load(f)
            tools_data = data.get("tools", [])
            if isinstance(tools_data, dict): tools = list(tools_data.keys())
            elif isinstance(tools_data, list): tools = tools_data

    tool_shortcut_map = {}
    for t in tools:
        sn = t.split(".")[-1] if "." in t else t
        tool_shortcut_map[sn] = t

    python_extra_links = {"pip", "pip3", "python3", "python"}
    migrated = 0
    deferred_extras = []

    # Pass 1: migrate tool shortcuts (create bin/<tool>/<tool>)
    for f in list(bin_dir.iterdir()):
        if f.name == "TOOL" or f.name.startswith("."):
            continue
        if f.is_dir():
            continue

        if f.name in tool_shortcut_map:
            import tempfile
            tmp = tempfile.mktemp(dir=str(bin_dir), prefix=f".migrate_{f.name}_")
            shutil.move(str(f), tmp)
            tool_bin_dir = bin_dir / f.name
            tool_bin_dir.mkdir(exist_ok=True)
            dest = tool_bin_dir / f.name
            if dest.exists() or dest.is_symlink():
                os.remove(dest)
            shutil.move(tmp, str(dest))
            print(f"  {BOLD}{BLUE}Migrated{RESET}: bin/{f.name} -> bin/{f.name}/{f.name}")
            migrated += 1

            from logic.utils import register_path
            register_path(tool_bin_dir)

        elif f.name in python_extra_links:
            deferred_extras.append(f)

    # Pass 2: migrate python extra symlinks (pip, pip3, python3)
    for f in deferred_extras:
        if not f.exists():
            continue
        python_bin_dir = bin_dir / "PYTHON"
        python_bin_dir.mkdir(exist_ok=True)
        dest = python_bin_dir / f.name
        if dest.exists() or dest.is_symlink():
            os.remove(dest)
        shutil.move(str(f), str(dest))
        print(f"  {BOLD}{BLUE}Migrated{RESET}: bin/{f.name} -> bin/PYTHON/{f.name}")
        migrated += 1

    if migrated == 0:
        print(f"{BOLD}{GREEN}Success{RESET}: No legacy flat shortcuts to migrate.")
    else:
        print(f"\n{BOLD}{GREEN}Successfully migrated{RESET} {migrated} shortcut(s) to bin/<tool>/ structure.")

    return True

