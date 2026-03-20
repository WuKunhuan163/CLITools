"""TOOL --migrate --<level> <domain> [options]

Unified migration framework for importing tools, infrastructure, hooks,
MCP servers, skills, and information from external sources.
"""

import sys

from logic._._ import EcoCommand


class MigrateCommand(EcoCommand):
    name = "migrate"
    usage = "TOOL --migrate --<level> <domain> [options]"

    def handle(self, args):
        from .core import (
            list_domains, execute_migration, MIGRATION_LEVELS,
            get_domain_info, check_pending, scan_domain,
        )

        if not args or args[0] in ("-h", "--help", "help"):
            return self._help(list_domains, MIGRATION_LEVELS)

        if args[0] == "--list":
            return self._list(list_domains, check_pending)

        if args[0] == "--scan":
            return self._scan(args[1:], scan_domain)

        level, domain, namespace, remaining = self._parse_level_domain(args, MIGRATION_LEVELS)

        if not level:
            self.error("Missing level.", "Use --<level> (e.g. --draft-tool, --infrastructure)")
            return 1
        if not domain:
            self.error("Missing domain.", "Specify a domain name (e.g. CLI-Anything, astral-sh)")
            return 1

        info = get_domain_info(domain)
        if not info:
            self.error("Unknown domain.", domain)
            domains = list_domains()
            if domains:
                print(f"  Available: {', '.join(d['domain'] for d in domains)}")
            return 1

        if namespace:
            remaining.extend(["--namespace", namespace])

        code = execute_migration(domain, level, remaining)
        sys.exit(code)

    def _help(self, list_domains_fn, levels):
        self.header(f"{self.tool_name} --migrate")
        print(f"  Usage: {self.tool_name} --migrate --<level> <domain> [options]\n")
        print(f"  {self.BOLD}Levels{self.RESET}")
        for lv in levels:
            print(f"    --{lv}")
        print(f"\n  {self.BOLD}Sub-commands{self.RESET}")
        print(f"    --list                    List all migration domains")
        print(f"    --scan <domain>           Discover available items in a domain")
        print(f"    --namespace <N>           Scope to a specific sub-source")
        print(f"\n  {self.BOLD}Domains{self.RESET}")
        for d in list_domains_fn():
            name = d.get("domain", "?")
            desc = d.get("description", "")[:60]
            levels_str = ", ".join(d.get("levels", []))
            print(f"    {name:20s} [{levels_str}]")
            if desc:
                print(f"    {self.DIM}{desc}{self.RESET}")
        print(f"\n  {self.BOLD}Examples{self.RESET}")
        print(f"    {self.tool_name} --migrate --list")
        print(f"    {self.tool_name} --migrate --scan CLIANYTHING")
        print(f"    {self.tool_name} --migrate --scan CLIANYTHING --namespace blender")
        print(f"    {self.tool_name} --migrate --draft-tool CLIANYTHING blender")
        print(f"    {self.tool_name} --migrate --infrastructure astral-sh --version 3.12 --platform macos-arm64")
        print(f"    {self.tool_name} --migrate --draft-tool CLIANYTHING --all")
        return 0

    def _list(self, list_domains_fn, check_pending_fn):
        domains = list_domains_fn()
        if not domains:
            print(f"  {self.BOLD}No migration domains found.{self.RESET}")
            return 0
        print(f"  {self.BOLD}Migration domains{self.RESET} ({len(domains)})\n")
        for d in domains:
            name = d.get("domain", "?")
            desc = d.get("description", "")[:70]
            levels_str = ", ".join(d.get("levels", []))
            status = check_pending_fn(name)
            migrated = status.get("migrated", 0)
            total = status.get("total", "?")
            print(f"    {self.BOLD}{name}{self.RESET}")
            if desc:
                print(f"    {self.DIM}{desc}{self.RESET}")
            print(f"    Levels: {levels_str}")
            print(f"    Status: {migrated}/{total} migrated")
            print()
        return 0

    def _scan(self, args, scan_domain_fn):
        domain = args[0] if args else None
        if not domain:
            self.error("Missing domain.", f"Usage: {self.tool_name} --migrate --scan <domain> [--namespace <N>]")
            return 1
        ns = None
        if "--namespace" in args:
            ns_idx = args.index("--namespace")
            if ns_idx + 1 < len(args):
                ns = args[ns_idx + 1]
        result = scan_domain_fn(domain, namespace=ns)
        if "error" in result:
            self.error("Scan failed.", result["error"])
            return 1
        available = result.get("available", [])
        migrated = result.get("migrated", [])
        pending = result.get("pending", [])
        print(f"  {self.BOLD}Scan: {domain}{self.RESET} — {len(available)} items found\n")
        if migrated:
            print(f"  {self.BOLD}Migrated{self.RESET} ({len(migrated)})")
            for item in migrated:
                print(f"    {self.GREEN}{item['name']:20s}{self.RESET} -> {item.get('tool', '?'):14s} [{item.get('status', 'draft')}]")
        if pending:
            print(f"  {self.BOLD}Available{self.RESET} ({len(pending)})")
            for item in pending:
                print(f"    {item['name']:20s} -> {item.get('tool', '?')}")
        if not migrated and not pending:
            self.info("No items found.")
        return 0

    @staticmethod
    def _parse_level_domain(args, levels):
        level = None
        domain = None
        namespace = None
        remaining = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--") and arg[2:] in levels:
                level = arg[2:]
            elif arg == "--namespace" and i + 1 < len(args):
                namespace = args[i + 1]
                i += 1
            elif domain is None and not arg.startswith("-"):
                domain = arg
            else:
                remaining.append(arg)
            i += 1
        return level, domain, namespace, remaining
