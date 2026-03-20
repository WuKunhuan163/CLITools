"""USERINPUT --config — Configuration management subcommand.

Handles: --config (show all), --config --focus-interval, --config --time-increment,
         --config --cpu-limit, --config --cpu-timeout.

Also handles: --enquiry-mode on/off/status
"""
import sys
import json

from tool.USERINPUT.logic import get_config, save_config, get_msg


def run_config(tool, args, unknown=None):
    """Dispatch config subcommands. Called from main.py."""
    config = get_config()
    updated = False

    if args.focus_interval is not None:
        config["focus_interval"] = args.focus_interval
        updated = True
    if args.time_increment is not None:
        config["time_increment"] = args.time_increment
        updated = True
    if args.cpu_limit is not None:
        config["cpu_limit"] = args.cpu_limit
        updated = True
    if args.cpu_timeout is not None:
        config["cpu_timeout"] = args.cpu_timeout
        updated = True

    from interface.config import get_color
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    if not updated:
        print(f"{BOLD}USERINPUT configuration{RESET}:")
        for k, v in config.items():
            if k == "system_prompt":
                continue
            print(f"  {k}: {v}")
        return 0

    save_config(config)
    print(f"{BOLD}{GREEN}{get_msg('label_successfully_updated', 'Successfully updated')}{RESET} USERINPUT configuration:")
    for k, v in config.items():
        if k == "system_prompt":
            continue
        print(f"  {k}: {v}")
    return 0


def run_enquiry_mode(tool, args):
    """Handle --enquiry-mode on/off/status."""
    from interface.config import get_color
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    config = get_config()
    mode = args.enquiry_mode

    if mode == 'on':
        config["enquiry_mode"] = True
        save_config(config)
        print(f"{BOLD}{GREEN}Enabled{RESET} persistent enquiry mode. All USERINPUT calls will bypass the queue.")
        return 0
    elif mode == 'off':
        config["enquiry_mode"] = False
        save_config(config)
        print(f"{BOLD}{GREEN}Disabled{RESET} persistent enquiry mode. USERINPUT will check the queue first.")
        return 0
    else:
        is_on = config.get("enquiry_mode", False)
        status = f"{GREEN}on{RESET}" if is_on else "off"
        print(f"{BOLD}Enquiry mode{RESET}: {status}")
        return 0
