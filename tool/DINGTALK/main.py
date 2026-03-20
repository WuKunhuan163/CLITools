#!/usr/bin/env python3
"""DINGTALK Tool - DingTalk messaging and workspace integration via official API.

Uses the DingTalk Open Platform REST API (api.dingtalk.com + oapi.dingtalk.com).
No browser automation - fully ToS compliant.
"""
import sys
import json
import argparse
from pathlib import Path

script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
root_str = str(project_root)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

from interface.tool import ToolBase
from interface.config import get_color

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
DIM = get_color("DIM")
RESET = get_color("RESET")


class DINGTALKTool(ToolBase):
    def __init__(self):
        super().__init__("DINGTALK")

    def get_config_value(self, key):
        config_file = self.script_dir / "data" / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f).get(key)
            except Exception:
                pass
        return None

    def set_config_value(self, key, value):
        config_file = self.script_dir / "data" / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config = {}
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config = json.load(f)
            except Exception:
                pass
        config[key] = value
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)


_TUTORIAL_MAP = {
    "setup":      "setup_guide",
    "contacts":   "perm_contacts",
    "messaging":  "perm_messaging",
    "todo":       "perm_todo",
    "calendar":   "perm_calendar",
}


def _run_tutorial(name, tool):
    """Dispatch to the appropriate tutorial module."""
    if name == "list":
        print(f"\n  {BOLD}Available tutorials{RESET}")
        print(f"  {DIM}setup       Initial app creation and credentials{RESET}")
        print(f"  {DIM}contacts    Enable contact/address-book permissions{RESET}")
        print(f"  {DIM}messaging   Enable messaging & notification permissions{RESET}")
        print(f"  {DIM}todo        Enable Todo API permissions{RESET}")
        print(f"  {DIM}calendar    Enable Calendar API permissions{RESET}")
        print()
        return 0

    if name not in _TUTORIAL_MAP:
        print(f"  {BOLD}{RED}Unknown tutorial.{RESET} {DIM}{name}{RESET}")
        print(f"  Available: {', '.join(_TUTORIAL_MAP.keys())}, list")
        return 1

    if name == "setup":
        import importlib.util
        tutorial_mod = Path(__file__).resolve().parent / "logic" / "command" / "tutorial_cmd.py"
        spec = importlib.util.spec_from_file_location("dingtalk_tutorial_cmd", str(tutorial_mod))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.execute(tool)

    check = _check_setup_prereq()
    if not check["ok"]:
        print(f"  {BOLD}{RED}Setup required.{RESET} {check['error']}")
        print(f"  Run: DINGTALK --tutorial setup")
        return 1

    module_name = _TUTORIAL_MAP[name]
    import importlib
    mod = importlib.import_module(f"tool.DINGTALK.logic.tutorial.{module_name}.main")

    from tool.DINGTALK.logic.command.tutorial_cmd import _make_step_callback
    result = mod.run(on_step_change=_make_step_callback())

    import sys as _sys
    _sys.stdout.write("\r\033[K")
    _sys.stdout.flush()

    if result and result.get("status") == "success":
        print(f"  {BOLD}{GREEN}Completed.{RESET} {DIM}{name} permissions tutorial{RESET}")
        return 0
    else:
        reason = (result or {}).get("reason") or (result or {}).get("status") or "Exited"
        print(f"  {BOLD}{RED}Tutorial exited.{RESET} {reason}")
        return 1


def _check_setup_prereq():
    """Quick check if setup tutorial has been completed."""
    config_file = Path(__file__).resolve().parent / "data" / "config.json"
    if not config_file.exists():
        return {"ok": False, "error": "No configuration found. Run: DINGTALK --tutorial setup"}
    try:
        cfg = json.loads(config_file.read_text())
    except Exception:
        return {"ok": False, "error": "Configuration file is corrupted."}
    if not cfg.get("app_key") or not cfg.get("app_secret"):
        return {"ok": False, "error": "Credentials not configured."}
    return {"ok": True}


def _print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    tool = DINGTALKTool()

    parser = argparse.ArgumentParser(
        description="DingTalk messaging and workspace integration (official API)",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("args", nargs="*", help="Additional arguments")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--type", default="text", choices=["text", "markdown"], help="Message type")
    parser.add_argument("--title", default=None, help="Title for markdown messages")
    parser.add_argument("--phone", default=None, help="Phone number for contact lookup or messaging")
    parser.add_argument("--userid", default=None, help="DingTalk userId")
    parser.add_argument("--webhook", default=None, help="Webhook URL for group messages")
    parser.add_argument("--tutorial", nargs="?", const="setup", default=None,
                        metavar="NAME",
                        help="Run interactive tutorial (setup, contacts, messaging, todo, calendar)")
    parser.add_argument("--setup-tutorial", action="store_true", dest="setup_tutorial",
                        help=argparse.SUPPRESS)

    if tool.handle_command_line(parser):
        return

    args, unknown = parser.parse_known_args()
    cmd = args.command

    tutorial_name = getattr(args, 'tutorial', None)
    if getattr(args, 'setup_tutorial', False):
        tutorial_name = "setup"

    if tutorial_name is not None:
        sys.exit(_run_tutorial(tutorial_name, tool))

    if cmd == "status":
        from tool.DINGTALK.logic.api import _load_config
        cfg = _load_config()
        has_key = bool(cfg.get("app_key"))
        has_secret = bool(cfg.get("app_secret"))
        has_agent = bool(cfg.get("agent_id"))
        has_operator = bool(cfg.get("operator_id"))

        print(f"\n  {BOLD}DINGTALK{RESET} tool status")
        print(f"  {DIM}API: DingTalk Open Platform (official REST API){RESET}")
        print()
        print(f"  app_key:     {'configured' if has_key else 'not set'}")
        print(f"  app_secret:  {'configured' if has_secret else 'not set'}")
        print(f"  agent_id:    {cfg.get('agent_id', 'not set')}")
        print(f"  operator_id: {cfg.get('operator_id', 'not set')}")
        print()
        print(f"  {BOLD}Capabilities{RESET}")
        print(f"  {DIM}send         Send robot 1:1 message by userId or phone{RESET}")
        print(f"  {DIM}send-group   Send robot message to group{RESET}")
        print(f"  {DIM}webhook      Send message via webhook robot{RESET}")
        print(f"  {DIM}notify       Send work notification{RESET}")
        print(f"  {DIM}contact      Look up user by phone or search{RESET}")
        print(f"  {DIM}todo         Create todo task{RESET}")
        print()
        return 0

    if cmd == "config":
        if not args.args or len(args.args) < 2:
            print(f"Usage: DINGTALK config <key> <value>")
            print(f"\n  Keys: app_key, app_secret, agent_id, operator_id, webhook_url, webhook_secret")
            return 1
        key, value = args.args[0], args.args[1]
        tool.set_config_value(key, value)
        masked = value[:4] + "****" if len(value) > 8 else "****"
        print(f"  {BOLD}{GREEN}Set.{RESET} {DIM}{key}={masked}{RESET}")
        return 0

    if cmd == "send":
        from tool.DINGTALK.logic.api import send_robot_message, send_message_to_phone
        content = " ".join(args.args) if args.args else None
        if not content:
            print(f"  {BOLD}{RED}Missing content.{RESET} Usage: DINGTALK send \"message\" --phone +86xxx")
            return 1

        if args.phone:
            result = send_message_to_phone(args.phone, content, args.type, args.title)
        elif args.userid:
            result = send_robot_message([args.userid], content, args.type, args.title)
        else:
            print(f"  {BOLD}{RED}Missing recipient.{RESET} Use --phone or --userid")
            return 1

        if args.json:
            _print_json(result)
        elif result.get("ok"):
            print(f"  {BOLD}{GREEN}Sent.{RESET} {DIM}{result.get('processQueryKey', '')}{RESET}")
        else:
            print(f"  {BOLD}{RED}Failed.{RESET} {result.get('error', 'Unknown error')}")
        return 0 if result.get("ok") else 1

    if cmd == "webhook":
        from tool.DINGTALK.logic.api import send_webhook_message, _load_config
        content = " ".join(args.args) if args.args else None
        if not content:
            print(f"  {BOLD}{RED}Missing content.{RESET} Usage: DINGTALK webhook \"message\"")
            return 1

        cfg = _load_config()
        webhook_url = args.webhook or cfg.get("webhook_url")
        if not webhook_url:
            print(f"  {BOLD}{RED}No webhook URL.{RESET} Use --webhook or: DINGTALK config webhook_url <URL>")
            return 1

        webhook_secret = cfg.get("webhook_secret")
        result = send_webhook_message(webhook_url, content, args.type, args.title, webhook_secret)
        if args.json:
            _print_json(result)
        elif result.get("ok"):
            print(f"  {BOLD}{GREEN}Sent.{RESET}")
        else:
            print(f"  {BOLD}{RED}Failed.{RESET} {result.get('error', 'Unknown error')}")
        return 0 if result.get("ok") else 1

    if cmd == "notify":
        from tool.DINGTALK.logic.api import send_work_notification
        content = " ".join(args.args) if args.args else None
        if not content:
            print(f"  {BOLD}{RED}Missing content.{RESET} Usage: DINGTALK notify \"message\" --userid xxx")
            return 1

        user_ids = [args.userid] if args.userid else None
        result = send_work_notification(user_ids, content, args.type, args.title)
        if args.json:
            _print_json(result)
        elif result.get("ok"):
            print(f"  {BOLD}{GREEN}Sent.{RESET} {DIM}task_id={result.get('task_id')}{RESET}")
        else:
            print(f"  {BOLD}{RED}Failed.{RESET} {result.get('error', 'Unknown error')}")
        return 0 if result.get("ok") else 1

    if cmd == "contact":
        from tool.DINGTALK.logic.api import get_user_by_mobile, get_user_detail, search_users
        query = args.args[0] if args.args else args.phone
        if not query:
            print(f"  {BOLD}{RED}Missing query.{RESET} Usage: DINGTALK contact <name_or_phone>")
            return 1

        if query.replace("+", "").replace("-", "").isdigit():
            phone = query.lstrip("+").lstrip("86")
            result = get_user_by_mobile(phone)
            if result.get("ok") and result.get("userid"):
                detail = get_user_detail(result["userid"])
                if detail.get("ok"):
                    result = detail
        else:
            result = search_users(query)
            if result.get("ok") and result.get("userids"):
                detail = get_user_detail(result["userids"][0])
                if detail.get("ok"):
                    result["first_user"] = detail.get("user")

        if args.json:
            _print_json(result)
        elif result.get("ok"):
            user = result.get("user") or result.get("first_user")
            if user:
                print(f"  {BOLD}{user.get('name', '?')}{RESET}")
                print(f"  {DIM}userId:  {user.get('userid', '?')}{RESET}")
                print(f"  {DIM}mobile:  {user.get('mobile', '?')}{RESET}")
                print(f"  {DIM}title:   {user.get('title', '?')}{RESET}")
                print(f"  {DIM}email:   {user.get('email', '?')}{RESET}")
            elif result.get("userid"):
                print(f"  {BOLD}Found.{RESET} {DIM}userId={result['userid']}{RESET}")
            else:
                print(f"  {BOLD}Found.{RESET} {DIM}{result.get('total', 0)} users{RESET}")
        else:
            print(f"  {BOLD}{RED}Not found.{RESET} {result.get('error', '')}")
        return 0 if result.get("ok") else 1

    if cmd == "todo":
        from tool.DINGTALK.logic.api import create_todo
        subject = " ".join(args.args) if args.args else None
        if not subject:
            print(f"  {BOLD}{RED}Missing subject.{RESET} Usage: DINGTALK todo \"task description\"")
            return 1

        result = create_todo(subject)
        if args.json:
            _print_json(result)
        elif result.get("ok"):
            print(f"  {BOLD}{GREEN}Created.{RESET} {DIM}id={result.get('task_id')}{RESET}")
        else:
            print(f"  {BOLD}{RED}Failed.{RESET} {result.get('error', 'Unknown error')}")
        return 0 if result.get("ok") else 1

    parser.print_help()
    print(f"\n  {BOLD}Commands{RESET}")
    print(f"  {DIM}status    Show configuration and capabilities{RESET}")
    print(f"  {DIM}config    Set credentials (app_key, app_secret, agent_id, ...){RESET}")
    print(f"  {DIM}send      Send robot 1:1 message (--phone or --userid){RESET}")
    print(f"  {DIM}webhook   Send message via webhook robot{RESET}")
    print(f"  {DIM}notify    Send work notification{RESET}")
    print(f"  {DIM}contact   Look up user by phone or name{RESET}")
    print(f"  {DIM}todo      Create todo task{RESET}")
    print()
    print(f"  {BOLD}Tutorials{RESET}  (--tutorial <name>)")
    print(f"  {DIM}setup     Initial app creation and credentials{RESET}")
    print(f"  {DIM}contacts  Enable contact/address-book permissions{RESET}")
    print(f"  {DIM}messaging Enable messaging & notification permissions{RESET}")
    print(f"  {DIM}todo      Enable Todo API permissions{RESET}")
    print(f"  {DIM}calendar  Enable Calendar API permissions{RESET}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
