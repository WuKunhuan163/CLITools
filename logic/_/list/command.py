"""TOOL --list [--force]

List all available tools and their installation status.
"""

import json

from logic._._ import EcoCommand


class ListCommand(EcoCommand):
    name = "list"
    usage = "TOOL --list [--force]"

    def handle(self, args):
        force = "--force" in args
        cache_path = self.project_root / "data" / "tools.json"

        cache = {}
        cached_used = False
        if not force and cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text())
                cached_used = True
            except Exception:
                pass

        if not cache or force:
            registry_path = self.project_root / "tool.json"
            if not registry_path.exists():
                self.error("Registry not found.")
                return 1

            tools_list = json.loads(registry_path.read_text()).get("tools", [])
            cache = {}
            for name in tools_list:
                tool_json = self.project_root / "tool" / name / "tool.json"
                info = {"installed": (self.project_root / "tool" / name).exists()}
                if tool_json.exists():
                    try:
                        data = json.loads(tool_json.read_text())
                        info["description"] = data.get("description", "No description")
                        info["purpose"] = data.get("purpose", "No purpose")
                    except Exception:
                        info["description"] = "Error reading tool.json"
                else:
                    info["description"] = self._(
                        "tool_not_found_locally",
                        "Not found locally (run 'TOOL install' to fetch)",
                    )
                    info["purpose"] = "N/A"
                cache[name] = info

            cache_path.parent.mkdir(exist_ok=True)
            cache_path.write_text(json.dumps(cache, indent=2))

        for name, info in sorted(cache.items()):
            status = "[installed]" if info.get("installed") else "[available]"
            print(f"{self.BOLD}{name}{self.RESET} {status}")
            print(f"  {info.get('description', 'No description')}")
            purpose_label = self._("tool_list_purpose_label", "Purpose:")
            print(f"  {purpose_label} {info.get('purpose', 'No purpose')}\n")

        if cached_used:
            warning_msg = self._(
                "tool_list_cache_warning",
                "Warning: Displaying cached data. Use --force to refresh.",
            )
            print(f"{self.BOLD}{self.YELLOW}{warning_msg}{self.RESET}")
        return 0
