"""TOOL --uninstall <TOOL_NAME> [-y]

Uninstall a tool with optional force-yes flag.
"""

import sys

from logic._._ import EcoCommand


class UninstallCommand(EcoCommand):
    name = "uninstall"
    usage = "TOOL --uninstall <TOOL_NAME> [-y]"

    def handle(self, args):
        if not args:
            self.print_usage()
            return 1
        force_yes = "-y" in args or "--yes" in args
        name = next((a for a in args if not a.startswith("-")), None)
        if not name:
            self.print_usage()
            return 1

        tool_dir = self.project_root / "tool" / name
        if not tool_dir.exists():
            self.error(
                self._("label_error", "Error") + ":",
                self._("tool_not_found_local", "Tool '{name}' is not installed.", name=name),
            )
            return 1

        if not force_yes:
            if sys.stdin.isatty():
                prompt = self._("confirm_uninstall",
                                "Are you sure you want to uninstall '{name}'? (y/N): ",
                                name=name)
                confirm = input(prompt)
                sys.stdout.write("\033[A\r\033[K")
                sys.stdout.flush()
                if confirm.lower() not in ("y", "yes"):
                    print(self._("uninstall_cancelled", "Uninstall cancelled."))
                    return 0
            else:
                print(self._("non_interactive_skip",
                             "Non-interactive session, skipping confirmation. Use -y to force."))
                return 1

        from logic._.setup.engine import ToolEngine
        engine = ToolEngine(name, self.project_root)
        return 0 if engine.uninstall() else 1
