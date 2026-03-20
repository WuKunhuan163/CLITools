"""TOOL --reinstall <TOOL_NAME>

Reinstall a tool by name. Delegates to ToolEngine.
"""

from logic._._ import EcoCommand


class ReinstallCommand(EcoCommand):
    name = "reinstall"
    usage = "TOOL --reinstall <TOOL_NAME>"

    def handle(self, args):
        if not args:
            self.print_usage()
            return 1
        from logic._.setup.engine import ToolEngine
        engine = ToolEngine(args[0], self.project_root)
        return 0 if engine.reinstall() else 1
