"""TOOL --config {set,show,show-lang}

Manage global AITerminalTools configuration.
"""

import json

from logic._._ import EcoCommand


class ConfigCommand(EcoCommand):
    name = "config"
    usage = "TOOL --config {set <key> <value> | show | show-lang}"

    def handle(self, args):
        parser = self.create_parser("Manage global AITerminalTools configuration")
        sub = parser.add_subparsers(dest="config_command")
        cs = sub.add_parser("set", help="Set a configuration value")
        cs.add_argument("key", help="Configuration key")
        cs.add_argument("value", help="Configuration value")
        sub.add_parser("show-lang", help="Show current language")
        sub.add_parser("show", help="Show all tool configurations")

        parsed = parser.parse_args(args)

        from interface.config import get_global_config
        from interface.utils import set_rtl_mode
        current_lang = get_global_config("language", "en")
        set_rtl_mode(current_lang in ["ar"])

        if parsed.config_command == "set":
            val = parsed.value
            if val.isdigit():
                val = int(val)
            return self._update(parsed.key, val)
        elif parsed.config_command == "show-lang":
            print(f"Current language: {current_lang}")
        elif parsed.config_command == "show":
            self._show()
        else:
            parser.print_help()
        return 0

    def _update(self, key, value):
        from interface.config import set_global_config

        if key == "language":
            lang = value.lower() if isinstance(value, str) else value
            if lang != "en":
                trans_path = self.project_root / "logic" / "translation" / f"{lang}.json"
                if not trans_path.exists():
                    self.error(
                        self._("label_error", "Error") + ":",
                        self._("lang_error_not_found_simple", "Language '{lang}' not found.", lang=lang),
                    )
                    return 1

        is_auto = False
        if key == "terminal_width":
            if isinstance(value, str) and value.lower() == "auto":
                value = 0
                is_auto = True
            elif value == 0:
                is_auto = True

        if set_global_config(key, value):
            if key == "terminal_width":
                from interface.config import print_width_check
                print_width_check(value, is_auto=is_auto, project_root=self.project_root, translation_func=self._)
            else:
                print(self._("config_updated",
                             "Global configuration updated: {key} = {value}",
                             key=key, value=value))
            return 0
        return 1

    def _show(self):
        global_config_path = self.project_root / "data" / "config.json"

        self.header("Global Configuration")
        if global_config_path.exists():
            try:
                global_config = json.loads(global_config_path.read_text())
                for k, v in sorted(global_config.items()):
                    print(f"  {k}: {v}")
            except Exception:
                self.error("Error reading config")
        else:
            print("  (no global config)")

        tool_dir = self.project_root / "tool"
        tool_configs = []
        if tool_dir.exists():
            for td in sorted(tool_dir.iterdir()):
                config_path = td / "data" / "config.json"
                if config_path.exists():
                    try:
                        cfg = json.loads(config_path.read_text())
                        tool_configs.append((td.name, cfg))
                    except Exception:
                        tool_configs.append((td.name, {"_error": "unreadable"}))

        if tool_configs:
            self.header("Tool Configurations")
            for name, cfg in tool_configs:
                items = ", ".join(f"{k}={v}" for k, v in cfg.items() if not k.startswith("_"))
                if items:
                    print(f"  {name}: {items}")
                elif "_error" in cfg:
                    print(f"  {name}: {self.RED}error{self.RESET}")
        print()
