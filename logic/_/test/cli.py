"""TOOL --test [tool_name] [options]

Run unit tests for tools.
"""

import argparse

from logic._._ import EcoCommand


class TestCommand(EcoCommand):
    name = "test"
    usage = "TOOL --test [tool_name] [--range N M] [--max N] [--timeout N] [--list]"

    def handle(self, args):
        tp = argparse.ArgumentParser(add_help=False)
        tp.add_argument("tool_name", nargs="?", default="root", help="Tool name or 'root'")
        tp.add_argument("--range", nargs=2, type=int, help="Test range (start end)")
        tp.add_argument("--max", type=int, default=3, help="Max concurrent tests")
        tp.add_argument("--timeout", type=int, default=60, help="Test timeout")
        tp.add_argument("--list", action="store_true", help="List tests only")
        tp.add_argument("-no-warning", "--no-warning", action="store_true")
        parsed = tp.parse_args(args)

        from interface.test import test_tool_with_args
        test_tool_with_args(parsed, self.project_root, translation_func=self._)
        return 0
