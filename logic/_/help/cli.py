"""TOOL ---help — Hierarchical help generated from argparse.json DFS traversal.

Unlike argparse's native --help, this eco command discovers all command
endpoints by walking the logic/_/ directory tree and reading each level's
argparse.json descriptor. The result is a DFS tree showing the full
command surface.

Usage:
    TOOL ---help               Show full command tree
    TOOL ---help <command>     Show help for a specific command subtree
    TOOL ---help --json        Output as JSON (for programmatic use)
"""

import json
from pathlib import Path

from logic._._ import EcoCommand


class HelpCommand(EcoCommand):
    name = "help"
    usage = "TOOL ---help [command] [--json]"

    def handle(self, args):
        as_json = "--json" in args
        filter_cmd = None
        for a in args:
            if not a.startswith("-"):
                filter_cmd = a
                break

        tree = self._build_tree()

        if filter_cmd:
            subtree = self._find_subtree(tree, filter_cmd)
            if subtree:
                tree = [subtree]
            else:
                self.error(f"Command not found: {filter_cmd}")
                self.info("Run TOOL ---help for the full command tree.")
                return 1

        if as_json:
            print(json.dumps(tree, indent=2, ensure_ascii=False))
        else:
            self._print_tree(tree)

        return 0

    def _build_tree(self):
        """Build the command tree by DFS-walking logic/_/ directories."""
        shared_dir = self.project_root / "logic" / "_"
        nodes = []

        if not shared_dir.exists():
            return nodes

        for d in sorted(shared_dir.iterdir()):
            if not d.is_dir() or d.name.startswith((".", "_")):
                continue
            if not (d / "cli.py").exists():
                continue

            node = self._build_node(d, prefix="---")
            if node:
                nodes.append(node)

        return nodes

    def _build_node(self, directory, prefix="---"):
        """Build a tree node from a directory's argparse.json."""
        argparse_file = directory / "argparse.json"
        name = directory.name

        node = {
            "name": name,
            "prefix": prefix,
            "command": f"{prefix}{name}",
            "description": "",
            "children": [],
        }

        if argparse_file.exists():
            try:
                schema = json.loads(argparse_file.read_text(encoding="utf-8"))
                node["description"] = schema.get("description", "")

                for sub_name, sub_schema in schema.get("subcommands", {}).items():
                    child = {
                        "name": sub_name,
                        "prefix": "",
                        "command": f"{prefix}{name} {sub_name}",
                        "description": sub_schema.get("description", ""),
                        "args": sub_schema.get("args", []),
                        "children": [],
                    }
                    node["children"].append(child)
            except (json.JSONDecodeError, KeyError):
                pass

        # Check for nested directories with their own argparse.json
        for sub_dir in sorted(directory.iterdir()):
            if not sub_dir.is_dir() or sub_dir.name.startswith((".", "_")):
                continue
            if (sub_dir / "argparse.json").exists() or (sub_dir / "cli.py").exists():
                child_node = self._build_node(sub_dir, prefix="")
                if child_node:
                    child_node["command"] = f"{prefix}{name} {child_node['name']}"
                    node["children"].append(child_node)

        return node

    def _find_subtree(self, tree, command):
        """Find a command node by name (DFS)."""
        for node in tree:
            if node["name"] == command:
                return node
            result = self._find_subtree(node.get("children", []), command)
            if result:
                return result
        return None

    def _print_tree(self, nodes, depth=0):
        """Print the command tree as an indented DFS display."""
        if depth == 0:
            self.header(f"{self.tool_name} Command Tree")
            print(f"  {self.DIM}Prefix: ---<eco>  --<tool>  -<modifier>{self.RESET}\n")

        for i, node in enumerate(nodes):
            is_last = i == len(nodes) - 1
            connector = "└── " if is_last else "├── "
            indent = "    " * depth

            cmd_display = node.get("command", node["name"])
            desc = node.get("description", "")

            if depth == 0:
                print(f"  {self.BOLD}{cmd_display}{self.RESET}")
                if desc:
                    print(f"    {self.DIM}{desc}{self.RESET}")
            else:
                print(f"  {indent}{connector}{self.BOLD}{node['name']}{self.RESET}")
                if desc:
                    child_indent = "    " * (depth + 1) if not is_last else "    " * (depth + 1)
                    print(f"  {child_indent}{self.DIM}{desc}{self.RESET}")

            # Print args if any
            for arg in node.get("args", []):
                arg_indent = "    " * (depth + 1)
                arg_name = arg.get("name", "")
                arg_help = arg.get("help", "")
                if arg_name:
                    print(f"  {arg_indent}  {self.DIM}{arg_name}  {arg_help}{self.RESET}")

            children = node.get("children", [])
            if children:
                child_depth = depth + 1 if depth > 0 else 1
                self._print_tree(children, child_depth)

        if depth == 0:
            print(f"\n  {self.DIM}Use {self.tool_name} ---help <command> for details.{self.RESET}")
