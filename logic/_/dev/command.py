"""TOOL --dev <subcommand>

Extended dev operations: sync, reset, enter, create, sanity-check, audit-test,
audit-bin, audit-archived, migrate-bin, install/uninstall-hooks, locker, docs, report.
"""

from logic._._ import EcoCommand


class DevCommand(EcoCommand):
    name = "dev"
    usage = "TOOL --dev <command>"

    def handle(self, args):
        subcmd = args[0] if args else ""
        rest = args[1:] if len(args) > 1 else []

        dispatch = {
            "sync": self._sync,
            "reset": self._reset,
            "enter": lambda: self._enter(rest),
            "create": lambda: self._create(rest),
            "create-rule": lambda: self._create_rule(rest),
            "show-rule": lambda: self._show_rule(rest),
            "inject-rule": self._inject_rule,
            "sanity-check": lambda: self._sanity_check(rest),
            "audit-test": lambda: self._audit_test(rest),
            "audit-bin": lambda: self._audit_bin(rest),
            "audit-archived": self._audit_archived,
            "migrate-bin": self._migrate_bin,
            "archive": lambda: self._archive(rest),
            "unarchive": lambda: self._unarchive(rest),
            "push-resource": lambda: self._push_resource(rest),
            "install-hooks": self._install_hooks,
            "uninstall-hooks": self._uninstall_hooks,
            "hooks": lambda: self._hooks(rest),
            "call-register": lambda: self._call_register(rest),
            "locker": self._locker,
            "docs": lambda: self._docs(rest),
            "report": lambda: self._report(rest),
        }

        handler = dispatch.get(subcmd)
        if handler:
            handler()
            return 0
        self._print_help()
        return 0

    def _sync(self):
        from interface.dev import dev_sync
        dev_sync(self.project_root, translation_func=self._)

    def _reset(self):
        from interface.dev import dev_reset
        from interface.utils import get_logic_dir
        dev_reset(self.project_root, get_logic_dir(self.project_root), translation_func=self._)

    def _enter(self, rest):
        branch = rest[0] if rest else None
        if branch not in ("main", "test"):
            print(f"Usage: {self.tool_name} --dev enter <main|test> [-f]")
            return
        from interface.dev import dev_enter
        dev_enter(branch, self.project_root, force="-f" in rest or "--force" in rest, translation_func=self._)

    def _create(self, rest):
        name = rest[0] if rest else None
        if not name:
            print(f"Usage: {self.tool_name} --dev create <tool_name>")
            return
        from interface.dev import dev_create
        dev_create(name, self.project_root, translation_func=self._)

    def _sanity_check(self, rest):
        name = rest[0] if rest else None
        if not name:
            print(f"Usage: {self.tool_name} --dev sanity-check <tool_name> [--fix]")
            return
        from interface.dev import dev_sanity_check
        dev_sanity_check(name, self.project_root, fix="--fix" in rest, translation_func=self._)

    def _audit_test(self, rest):
        name = rest[0] if rest else None
        if not name:
            print(f"Usage: {self.tool_name} --dev audit-test <tool_name> [--fix]")
            return
        from interface.dev import dev_audit_test
        dev_audit_test(name, self.project_root, fix="--fix" in rest)

    def _audit_bin(self, rest):
        from interface.dev import dev_audit_bin
        dev_audit_bin(self.project_root, fix="--fix" in rest)

    def _audit_archived(self):
        from interface.dev import dev_audit_archived
        dev_audit_archived(self.project_root)

    def _migrate_bin(self):
        from interface.dev import dev_migrate_bin
        dev_migrate_bin(self.project_root)

    def _archive(self, rest):
        name = rest[0] if rest else None
        if not name:
            print(f"Usage: {self.tool_name} --dev archive <tool_name>")
            return
        from interface.dev import dev_archive_tool
        dev_archive_tool(name, self.project_root)

    def _unarchive(self, rest):
        name = rest[0] if rest else None
        if not name:
            print(f"Usage: {self.tool_name} --dev unarchive <tool_name>")
            return
        from interface.dev import dev_unarchive_tool
        dev_unarchive_tool(name, self.project_root)

    def _push_resource(self, rest):
        if not rest:
            print(f"Usage: {self.tool_name} --dev push-resource <tool_name> [<version>]")
            print(f"  Pushes binary resources from logic/_/dev/resource/<tool>/ to remote tool branch.")
            return
        tool_name = rest[0]
        version = rest[1] if len(rest) > 1 else None
        from interface.dev import dev_push_resource
        dev_push_resource(tool_name, self.project_root, version=version)

    def _install_hooks(self):
        from interface.git import install_hooks
        if install_hooks(self.project_root):
            self.success("Installed", "post-checkout hook.")
        else:
            self.warn("Skipped:", "hook already exists or .git not found.")

    def _uninstall_hooks(self):
        from interface.git import uninstall_hooks
        if uninstall_hooks(self.project_root):
            self.success("Removed", "post-checkout hook.")
        else:
            self.warn("Skipped:", "no AITerminalTools hook found.")

    def _hooks(self, rest):
        from interface.tool import ToolBase as _ToolBase
        root_tool = _ToolBase("TOOL", is_root=True)
        root_tool._handle_hooks_command(rest)

    def _call_register(self, rest):
        from interface.tool import ToolBase as _ToolBase
        root_tool = _ToolBase("TOOL", is_root=True)
        root_tool._handle_call_register(rest)

    def _locker(self):
        from interface.git import get_persistence_manager
        pm = get_persistence_manager(self.project_root)
        lockers = pm.list_lockers()
        if not lockers:
            self.info("No lockers.")
        else:
            for l in lockers:
                branch = l.get("branch", "?")
                size = l.get("size_mb", 0)
                print(f"  {self.BOLD}{l['key']}{self.RESET}: branch={branch}, size={size}MB")

    def _docs(self, rest):
        from interface.dev import list_docs
        scope = rest[0] if rest else "root"
        docs = list_docs(scope)
        print(f"  {self.BOLD}Docs at{self.RESET} {self.DIM}{docs['path']}{self.RESET}")
        print(f"  README:    {docs['readme'] or self.DIM + 'none' + self.RESET}")
        print(f"  for_agent: {docs['for_agent'] or self.DIM + 'none' + self.RESET}")
        reports = docs["reports"]
        if reports:
            print(f"  Reports ({len(reports)}):")
            for r in reports[:15]:
                print(f"    {self.DIM}{r['name']}{self.RESET}")
        else:
            print(f"  Reports:   {self.DIM}none{self.RESET}")

    def _report(self, rest):
        if not rest:
            print(f"Usage: {self.tool_name} --dev report <scope> <topic>")
            print(f"  scope: root, tool/LLM, provider/zhipu, etc.")
            print(f"  topic: short description (becomes filename)")
            return
        scope = rest[0]
        topic = " ".join(rest[1:]) if len(rest) > 1 else "untitled"
        from interface.dev import create_report
        content = f"# {topic}\n\n## Summary\n\n(Fill in)\n\n## Changes Made\n\n## Issues Found & Fixed\n\n## Next Steps\n"
        path = create_report(scope, topic, content)
        self.success("Created", f"{self.DIM}{path}{self.RESET}")

    def _create_rule(self, rest):
        if not rest:
            print(f"Usage: {self.tool_name} --dev create-rule <name> --description <desc> [--globs <patterns>] [--always-apply]")
            return
        name = rest[0]
        desc = ""
        globs = None
        always_apply = False
        i = 1
        while i < len(rest):
            if rest[i] == "--description" and i + 1 < len(rest):
                desc = rest[i + 1]; i += 2
            elif rest[i] == "--globs" and i + 1 < len(rest):
                globs = rest[i + 1]; i += 2
            elif rest[i] == "--always-apply":
                always_apply = True; i += 1
            else:
                i += 1
        if not desc:
            self.error("Missing --description.")
            return

        rules_dir = self.project_root / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        rule_path = rules_dir / f"{name}.mdc"
        globs_line = globs or ""
        content = f"""---
description: {desc}
globs: {globs_line}
alwaysApply: {"true" if always_apply else "false"}
---

# {name}

(Fill in rule content here)
"""
        rule_path.write_text(content, encoding="utf-8")
        self.success("Created", f"{self.DIM}{rule_path}{self.RESET}")

    def _show_rule(self, rest):
        target = rest[0] if rest else None
        from interface.config import generate_ai_rule
        generate_ai_rule(self.project_root, target_tool=target, translation_func=self._)

    def _inject_rule(self):
        from interface.config import inject_rule
        inject_rule(self.project_root, translation_func=self._)

    def _print_help(self):
        print(f"Usage: {self.tool_name} --dev <command>")
        print(f"\n{self.BOLD}Available commands:{self.RESET}")
        cmds = [
            ("sync", "Sync dev -> tool -> main -> test"),
            ("reset", "Reset main/test branches"),
            ("enter <main|test> [-f]", "Switch to branch"),
            ("create <name>", "Create a new tool template"),
            ("create-rule <name> --description ..", "Create a Cursor rule (.mdc)"),
            ("show-rule [tool]", "Show the AI agent rule set"),
            ("inject-rule", "Inject rule into .cursor/rules/"),
            ("sanity-check <name> [--fix]", "Check tool structure"),
            ("audit-test <name> [--fix]", "Audit unit test naming"),
            ("audit-bin [--fix]", "Audit bin/ shortcuts"),
            ("audit-archived", "Check for duplicate tools"),
            ("archive <name>", "Archive a tool to logic/_/dev/archived/"),
            ("unarchive <name>", "Restore an archived tool to tool/"),
            ("push-resource <tool> [ver]", "Push binary resources to remote tool branch"),
            ("migrate-bin", "Migrate flat bin/ shortcuts"),
            ("install-hooks", "Install git post-checkout hook"),
            ("uninstall-hooks", "Remove git post-checkout hook"),
            ("hooks <sub>", "Manage tool hooks (list, run, etc.)"),
            ("call-register <sub>", "Manage tool call register"),
            ("locker", "List persistence lockers"),
            ("docs [scope]", "List README/for_agent/reports at scope"),
            ("report <scope> <topic>", "Create a new report"),
        ]
        for cmd, desc in cmds:
            print(f"  {cmd:<35} {desc}")
