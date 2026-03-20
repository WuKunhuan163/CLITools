"""TOOL --rule {create,inject}

AI rule management: create new rules, inject rules into IDE, or show current.
Delegates actual rule generation to tool/IDE/logic/rule (via interface.config).
"""

import argparse

from logic._._ import EcoCommand


class RuleCommand(EcoCommand):
    name = "rule"
    usage = "TOOL --rule [create <name> --description <desc> | inject]"

    def handle(self, args):
        rp = argparse.ArgumentParser(
            prog=f"{self.tool_name} --rule",
            description="AI rule management",
        )
        sub = rp.add_subparsers(dest="rule_command")
        rc = sub.add_parser("create", help="Create a Cursor rule (.mdc)")
        rc.add_argument("name", help="Rule name")
        rc.add_argument("--description", required=True, help="Rule description")
        rc.add_argument("--globs", help="File patterns (comma separated)")
        rc.add_argument("--always-apply", action="store_true", help="Always apply this rule")
        sub.add_parser("inject", help="Inject TOOL rule into .cursor/rules/")

        parsed = rp.parse_args(args)

        if parsed.rule_command == "create":
            self._create(parsed.name, parsed.description, parsed.globs, parsed.always_apply)
        elif parsed.rule_command == "inject":
            self._inject()
        elif not parsed.rule_command:
            self._show()
        else:
            rp.print_help()
        return 0

    def _show(self):
        from interface.config import generate_ai_rule
        generate_ai_rule(self.project_root)

    def _inject(self):
        from interface.config import inject_rule
        inject_rule(self.project_root)

    def _create(self, name, description, globs, always_apply):
        from interface.config import generate_ai_rule
        generate_ai_rule(name, description, globs, always_apply, self.project_root)
