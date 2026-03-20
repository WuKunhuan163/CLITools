"""TOOL --install <TOOL_NAME>

Install a tool by name. Delegates to ToolEngine for the actual setup.
"""

from logic._._ import EcoCommand


class InstallCommand(EcoCommand):
    name = "install"
    usage = "TOOL --install <TOOL_NAME>"

    def handle(self, args):
        if not args:
            self.print_usage()
            return 1
        from logic._.setup.engine import ToolEngine
        engine = ToolEngine(args[0], self.project_root)
        return 0 if engine.install() else 1
