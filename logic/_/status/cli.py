"""TOOL --status

Display installed tools, configuration completeness, and health.
"""

import json

from logic._._ import EcoCommand


class StatusCommand(EcoCommand):
    name = "status"
    usage = "TOOL --status"

    def handle(self, args):
        registry_path = self.project_root / "tool.json"
        if not registry_path.exists():
            self.error("Registry not found.")
            return 1

        registry = json.loads(registry_path.read_text())
        all_tools = registry.get("tools", [])
        bin_dir = self.project_root / "bin"
        tool_dir = self.project_root / "tool"

        self.header("AITerminalTools Status")
        print(f"{'Tool':<20} {'Installed':<12} {'Config':<12} {'Tests':<10}")
        print("-" * 54)

        def _is_installed(n):
            sn = n.split(".")[-1] if "." in n else n
            return (bin_dir / sn / sn).exists() or (bin_dir / sn).is_file()

        installed_count = 0
        for name in sorted(all_tools):
            installed = _is_installed(name)
            has_main = (tool_dir / name / "main.py").exists()

            if installed and has_main:
                installed_str = f"{self.GREEN}yes{self.RESET}"
                installed_count += 1
            else:
                installed_str = f"{self.RED}no{self.RESET}"

            config_status = "-"
            config_path = tool_dir / name / "data" / "config.json"
            if config_path.exists():
                config_status = f"{self.GREEN}ok{self.RESET}"
            elif has_main:
                config_status = f"{self.YELLOW}none{self.RESET}"

            test_dir = tool_dir / name / "test"
            if test_dir.exists() and any(test_dir.glob("test_*.py")):
                test_count = len(list(test_dir.glob("test_*.py")))
                test_status = f"{test_count} test(s)"
            else:
                test_status = "-"

            print(f"  {name:<18} {installed_str:<21} {config_status:<21} {test_status}")

        print(f"\n{self.BOLD}{installed_count}/{len(all_tools)}{self.RESET} tools installed.\n")
        return 0
