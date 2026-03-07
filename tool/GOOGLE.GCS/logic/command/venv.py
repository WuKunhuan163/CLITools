#!/usr/bin/env python3
"""GCS venv command: manage remote Python virtual environments."""
import os
import sys
import json
import base64
from pathlib import Path

REMOTE_ENV_VENV = "/content/drive/MyDrive/REMOTE_ENV/venv"
VENV_STATES_FILE = f"{REMOTE_ENV_VENV}/venv_states.json"


def execute(tool, args, state_mgr, load_logic, unknown=None, **kwargs):
    venv_args = unknown or []

    if not venv_args or "--help" in venv_args or "-h" in venv_args:
        _show_help()
        return 0

    action = venv_args[0]
    env_names = venv_args[1:]
    utils = load_logic("utils")

    if action == "--create":
        if not env_names:
            print("venv: --create requires environment name(s)", file=sys.stderr)
            return 1
        return _venv_create(tool, state_mgr, load_logic, utils, env_names)

    elif action == "--delete":
        if not env_names:
            print("venv: --delete requires environment name(s)", file=sys.stderr)
            return 1
        return _venv_delete(tool, state_mgr, load_logic, utils, env_names)

    elif action == "--activate":
        if len(env_names) != 1:
            print("venv: --activate requires exactly one environment name", file=sys.stderr)
            return 1
        return _venv_activate(tool, state_mgr, load_logic, utils, env_names[0])

    elif action == "--deactivate":
        return _venv_deactivate(tool, state_mgr, load_logic, utils)

    elif action == "--list":
        return _venv_list(tool, state_mgr, load_logic, utils)

    elif action == "--current":
        return _venv_current(tool, state_mgr, load_logic, utils)

    elif action == "--protect":
        if not env_names:
            print("venv: --protect requires environment name(s)", file=sys.stderr)
            return 1
        return _venv_protect(tool, state_mgr, load_logic, utils, env_names, True)

    elif action == "--unprotect":
        if not env_names:
            print("venv: --unprotect requires environment name(s)", file=sys.stderr)
            return 1
        return _venv_protect(tool, state_mgr, load_logic, utils, env_names, False)

    else:
        print(f"venv: unknown action '{action}'", file=sys.stderr)
        _show_help()
        return 1


def _read_venv_states(tool, utils):
    """Read venv_states.json via Drive API."""
    config = utils.get_gcs_config(tool.project_root)
    env_folder_id = config.get("env_folder_id")
    if not env_folder_id:
        return {}

    venv_fid = _resolve_venv_folder(tool, utils, env_folder_id)
    if not venv_fid:
        return {}

    ok, data = utils.read_file_via_api(tool.project_root, venv_fid, "venv_states.json")
    if not ok:
        return {}
    try:
        return json.loads(data.get("content", "{}"))
    except json.JSONDecodeError:
        return {}


def _resolve_venv_folder(tool, utils, env_folder_id):
    """Resolve the @/venv/ folder ID."""
    script_body = f'''    import uuid
    env_id = {repr(env_folder_id)}
    q = f"'{{env_id}}' in parents and name = 'venv' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    params = {{"q": q, "fields": "files(id, name)", "pageSize": 10,
               "supportsAllDrives": "true", "includeItemsFromAllDrives": "true",
               "quotaUser": f"vf_{{uuid.uuid4().hex[:8]}}"}}
    r = api_get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
    if r.status_code == 200:
        files = r.json().get("files", [])
        for ff in files:
            if ff.get("name") == "venv":
                result = {{"folder_id": ff["id"]}}
                break
        else:
            result = {{"folder_id": None}}
    else:
        result = {{"error": f"API error {{r.status_code}}"}}'''

    ok, data = utils.run_drive_api_script(tool.project_root, script_body)
    if ok:
        return data.get("folder_id")
    return None


def _list_venv_dirs(tool, utils, env_folder_id):
    """List virtual environment directories under @/venv/."""
    venv_fid = _resolve_venv_folder(tool, utils, env_folder_id)
    if not venv_fid:
        return []

    ok, items = utils.list_folder_via_api(tool.project_root, venv_fid)
    if not ok:
        return []

    return [item["name"] for item in items
            if item.get("type") == "folder" and not item["name"].startswith(".")]


def _run_remote_cmd(tool, state_mgr, load_logic, utils, command):
    """Execute a remote shell command and return (success, result_dict)."""
    executor_mod = load_logic("executor")

    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid)
    current_logical = info.get("current_path", "~") if info else "~"
    remote_cwd = utils.logical_to_mount_path(current_logical)

    cdp_enabled = os.environ.get("GCS_CDP_ENABLED") == "1"
    script, metadata = executor_mod.generate_remote_command_script(
        tool.project_root, command, remote_cwd=remote_cwd, as_python=False,
        cdp_mode=cdp_enabled
    )

    command_result = {}

    def gui_action(stage=None):
        gui_queue_mod = load_logic("command/gui_queue")
        gui_q = gui_queue_mod.get_gui_queue(tool.project_root)
        logic_script = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic" / "executor.py")

        tmp_script = tool.project_root / "tmp" / f"gcs_venv_{metadata['ts']}.py"
        tmp_script.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_script, 'w') as f:
            f.write(script)

        gui_args = [
            "--command", f"venv operation",
            "--script-path", str(tmp_script),
            "--project-root", str(tool.project_root)
        ]
        if cdp_enabled:
            gui_args.append("--as-python")
        if metadata.get("done_marker"):
            gui_args.extend(["--done-marker", metadata["done_marker"]])
        if cdp_enabled:
            gui_args.append("--cdp-enabled")
        old_quiet = getattr(tool, "is_quiet", False)
        tool.is_quiet = True
        try:
            res = gui_q.run_gui_subprocess(
                tool, sys.executable, logic_script, 600,
                args=gui_args, request_id=f"venv_{metadata['ts']}"
            )
        finally:
            tool.is_quiet = old_quiet
        if tmp_script.exists():
            tmp_script.unlink()
        return res.get("status") == "success"

    def verify_action(stage=None):
        import time
        time.sleep(1.0)
        ok, msg, data = utils.wait_for_gdrive_file(
            tool.project_root, metadata["result_filename"], timeout=60, stage=stage
        )
        if ok:
            command_result.update(data)
            return True
        if stage:
            stage.error_brief = msg
        return False

    from logic.interface.turing import ProgressTuringMachine
    from logic.interface.turing import TuringStage

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage(
        "user action", gui_action,
        active_status="Waiting for", active_name="user action",
        fail_status="Failed", success_status="Completed",
        success_name="user action", bold_part="Waiting for user action"
    ))
    pm.add_stage(TuringStage(
        "command result", verify_action,
        active_status="Verifying", active_name="result",
        fail_status="Failed to verify", success_status="Retrieved",
        success_name="result", bold_part="Verifying result"
    ))

    if pm.run(ephemeral=True):
        return True, command_result
    return False, {}


def _venv_create(tool, state_mgr, load_logic, utils, env_names):
    from logic.interface.config import get_color
    GREEN, RED, BOLD, RESET = get_color("GREEN"), get_color("RED"), get_color("BOLD"), get_color("RESET")

    config = utils.get_gcs_config(tool.project_root)
    env_folder_id = config.get("env_folder_id")
    if not env_folder_id:
        print(f"{BOLD}{RED}Error{RESET}: env folder not configured. Run 'GCS --setup-tutorial'.", file=sys.stderr)
        return 1

    existing = _list_venv_dirs(tool, utils, env_folder_id)
    to_create = []
    for name in env_names:
        if name.startswith("."):
            print(f"{BOLD}{RED}Error{RESET}: name cannot start with '.'", file=sys.stderr)
            return 1
        if name in existing:
            print(f"Virtual environment '{name}' already exists, skipping.")
        else:
            to_create.append(name)

    if not to_create:
        return 0

    mkdir_parts = [f'mkdir -p "{REMOTE_ENV_VENV}/{n}"' for n in to_create]
    command = " && ".join(mkdir_parts)

    ok, result = _run_remote_cmd(tool, state_mgr, load_logic, utils, command)
    if ok:
        exit_code = result.get("exit_code", result.get("returncode", 0))
        if exit_code == 0:
            for n in to_create:
                print(f"{BOLD}{GREEN}Created{RESET} virtual environment '{n}'")
                print(f"  Path: {REMOTE_ENV_VENV}/{n}")
            return 0
    print(f"{BOLD}{RED}Error{RESET}: failed to create virtual environment(s)", file=sys.stderr)
    return 1


def _venv_delete(tool, state_mgr, load_logic, utils, env_names):
    from logic.interface.config import get_color
    GREEN, RED, YELLOW, BOLD, RESET = (
        get_color("GREEN"), get_color("RED"), get_color("YELLOW"), get_color("BOLD"), get_color("RESET")
    )

    states = _read_venv_states(tool, utils)
    protected = set()
    envs_data = states.get("environments", {})
    for ename, edata in envs_data.items():
        if isinstance(edata, dict) and edata.get("protected"):
            protected.add(ename)

    sid = state_mgr.get_active_shell_id()
    shell_data = states.get(sid, {})
    active_venv = shell_data.get("current_venv")

    to_delete = []
    for name in env_names:
        if name in protected:
            print(f"{BOLD}{YELLOW}Skipping{RESET} protected environment '{name}'")
        elif name == active_venv:
            print(f"{BOLD}{YELLOW}Skipping{RESET} currently active environment '{name}' (deactivate first)")
        else:
            to_delete.append(name)

    if not to_delete:
        return 0

    rm_parts = [f'rm -rf "{REMOTE_ENV_VENV}/{n}"' for n in to_delete]
    command = " && ".join(rm_parts)

    ok, result = _run_remote_cmd(tool, state_mgr, load_logic, utils, command)
    if ok:
        exit_code = result.get("exit_code", result.get("returncode", 0))
        if exit_code == 0:
            for n in to_delete:
                print(f"{BOLD}{GREEN}Deleted{RESET} virtual environment '{n}'")
            return 0
    print(f"{BOLD}{RED}Error{RESET}: failed to delete virtual environment(s)", file=sys.stderr)
    return 1


def _venv_activate(tool, state_mgr, load_logic, utils, env_name):
    from logic.interface.config import get_color
    GREEN, RED, YELLOW, BOLD, RESET = (
        get_color("GREEN"), get_color("RED"), get_color("YELLOW"), get_color("BOLD"), get_color("RESET")
    )

    sid = state_mgr.get_active_shell_id()
    states = _read_venv_states(tool, utils)
    shell_data = states.get(sid, {})
    current = shell_data.get("current_venv")

    if current == env_name:
        print(f"Virtual environment '{env_name}' is already active.")
        return 0

    config = utils.get_gcs_config(tool.project_root)
    env_folder_id = config.get("env_folder_id")
    if not env_folder_id:
        print(f"{BOLD}{RED}Error{RESET}: env folder not configured.", file=sys.stderr)
        return 1

    existing = _list_venv_dirs(tool, utils, env_folder_id)
    if env_name not in existing:
        print(f"{BOLD}{RED}Error{RESET}: virtual environment '{env_name}' does not exist.", file=sys.stderr)
        print(f"Available: {', '.join(existing) if existing else '(none)'}")
        return 1

    env_path = f"{REMOTE_ENV_VENV}/{env_name}"

    update_script = _generate_state_update_script(sid, env_name, env_path, "activate")
    command = f'python3 -c "import base64; exec(base64.b64decode(\'{base64.b64encode(update_script.encode()).decode()}\').decode())"'

    ok, result = _run_remote_cmd(tool, state_mgr, load_logic, utils, command)
    if ok:
        exit_code = result.get("exit_code", result.get("returncode", 0))
        if exit_code == 0:
            state_mgr.update_shell(sid, venv_name=env_name)
            print(f"{BOLD}{GREEN}Activated{RESET} virtual environment '{env_name}'")
            print(f"  PYTHONPATH includes: {env_path}")
            return 0

    print(f"{BOLD}{RED}Error{RESET}: failed to activate virtual environment.", file=sys.stderr)
    return 1


def _venv_deactivate(tool, state_mgr, load_logic, utils):
    from logic.interface.config import get_color
    GREEN, YELLOW, BOLD, RESET = get_color("GREEN"), get_color("YELLOW"), get_color("BOLD"), get_color("RESET")

    sid = state_mgr.get_active_shell_id()
    states = _read_venv_states(tool, utils)
    shell_data = states.get(sid, {})
    current = shell_data.get("current_venv")

    if not current:
        print(f"{BOLD}{YELLOW}No virtual environment is currently active.{RESET}")
        return 0

    update_script = _generate_state_update_script(sid, current, "", "deactivate")
    command = f'python3 -c "import base64; exec(base64.b64decode(\'{base64.b64encode(update_script.encode()).decode()}\').decode())"'

    ok, result = _run_remote_cmd(tool, state_mgr, load_logic, utils, command)
    if ok:
        exit_code = result.get("exit_code", result.get("returncode", 0))
        if exit_code == 0:
            state_mgr.update_shell(sid, venv_name="base")
            print(f"{BOLD}{GREEN}Deactivated{RESET} virtual environment '{current}'")
            return 0

    print(f"Error: failed to deactivate virtual environment.", file=sys.stderr)
    return 1


def _venv_list(tool, state_mgr, load_logic, utils):
    from logic.interface.config import get_color
    GREEN, BOLD, RESET = get_color("GREEN"), get_color("BOLD"), get_color("RESET")

    config = utils.get_gcs_config(tool.project_root)
    env_folder_id = config.get("env_folder_id")
    if not env_folder_id:
        print("Env folder not configured. Run 'GCS --setup-tutorial'.", file=sys.stderr)
        return 1

    env_names = _list_venv_dirs(tool, utils, env_folder_id)
    states = _read_venv_states(tool, utils)

    sid = state_mgr.get_active_shell_id()
    shell_data = states.get(sid, {})
    active = shell_data.get("current_venv")

    envs_data = states.get("environments", {})
    protected_set = set()
    for ename, edata in envs_data.items():
        if isinstance(edata, dict) and edata.get("protected"):
            protected_set.add(ename)

    if not env_names:
        print("No virtual environments found.")
        print("Create one with: GCS venv --create <name>")
        return 0

    print(f"{BOLD}Virtual environments ({len(env_names)} total):{RESET}")
    for name in sorted(env_names):
        marker = f"{GREEN}*{RESET}" if name == active else " "
        lock = " [protected]" if name in protected_set else ""
        print(f"  {marker} {name}{lock}")

    if active:
        print(f"\n  * = active in current shell")
    return 0


def _venv_current(tool, state_mgr, load_logic, utils):
    from logic.interface.config import get_color
    GREEN, BOLD, RESET = get_color("GREEN"), get_color("BOLD"), get_color("RESET")

    sid = state_mgr.get_active_shell_id()
    states = _read_venv_states(tool, utils)
    shell_data = states.get(sid, {})
    current = shell_data.get("current_venv")

    if current:
        env_path = shell_data.get("env_path", f"{REMOTE_ENV_VENV}/{current}")
        activated_at = shell_data.get("activated_at", "unknown")
        print(f"{BOLD}Current virtual environment:{RESET} {GREEN}{current}{RESET}")
        print(f"  Path: {env_path}")
        print(f"  Activated: {activated_at}")
    else:
        print("No virtual environment currently active.")
        print("Activate one with: GCS venv --activate <name>")
    return 0


def _venv_protect(tool, state_mgr, load_logic, utils, env_names, protected):
    from logic.interface.config import get_color
    GREEN, RED, BOLD, RESET = get_color("GREEN"), get_color("RED"), get_color("BOLD"), get_color("RESET")

    config = utils.get_gcs_config(tool.project_root)
    env_folder_id = config.get("env_folder_id")
    if not env_folder_id:
        print(f"{BOLD}{RED}Error{RESET}: env folder not configured.", file=sys.stderr)
        return 1

    existing = _list_venv_dirs(tool, utils, env_folder_id)
    valid = [n for n in env_names if n in existing]
    invalid = [n for n in env_names if n not in existing]

    if invalid:
        print(f"{BOLD}{RED}Not found:{RESET} {', '.join(invalid)}", file=sys.stderr)
    if not valid:
        return 1

    update_script = _generate_protect_script(valid, protected)
    command = f'python3 -c "import base64; exec(base64.b64decode(\'{base64.b64encode(update_script.encode()).decode()}\').decode())"'

    ok, result = _run_remote_cmd(tool, state_mgr, load_logic, utils, command)
    if ok:
        exit_code = result.get("exit_code", result.get("returncode", 0))
        if exit_code == 0:
            action = "Protected" if protected else "Unprotected"
            for n in valid:
                print(f"{BOLD}{GREEN}{action}{RESET} virtual environment '{n}'")
            return 0

    print(f"{BOLD}{RED}Error{RESET}: failed to update protection.", file=sys.stderr)
    return 1


def _generate_state_update_script(shell_id, env_name, env_path, action):
    """Generate Python script to update venv_states.json on the remote side."""
    return f"""
import json, os
from datetime import datetime

state_file = "{VENV_STATES_FILE}"
os.makedirs(os.path.dirname(state_file), exist_ok=True)

states = {{}}
if os.path.exists(state_file):
    try:
        with open(state_file, 'r') as f:
            states = json.load(f)
    except:
        states = {{}}

if "{action}" == "activate":
    states["{shell_id}"] = {{
        "current_venv": "{env_name}",
        "env_path": "{env_path}",
        "activated_at": datetime.now().isoformat(),
        "shell_id": "{shell_id}"
    }}
elif "{action}" == "deactivate":
    if "{shell_id}" in states:
        del states["{shell_id}"]

with open(state_file, 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)
"""


def _generate_protect_script(env_names, protected):
    """Generate Python script to update protection status in venv_states.json."""
    names_json = json.dumps(env_names)
    return f"""
import json, os

state_file = "{VENV_STATES_FILE}"
os.makedirs(os.path.dirname(state_file), exist_ok=True)

states = {{}}
if os.path.exists(state_file):
    try:
        with open(state_file, 'r') as f:
            states = json.load(f)
    except:
        states = {{}}

if "environments" not in states:
    states["environments"] = {{}}

for name in {names_json}:
    if name not in states["environments"]:
        states["environments"][name] = {{}}
    states["environments"][name]["protected"] = {protected}

with open(state_file, 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)
"""


def _show_help():
    print("""venv - manage remote Python virtual environments

Usage:
  GCS venv --create <name> [name2 ...]   Create virtual environment(s)
  GCS venv --delete <name> [name2 ...]   Delete virtual environment(s)
  GCS venv --activate <name>             Activate virtual environment
  GCS venv --deactivate                  Deactivate current environment
  GCS venv --list                        List all virtual environments
  GCS venv --current                     Show currently active environment
  GCS venv --protect <name> [...]        Protect environment from deletion
  GCS venv --unprotect <name> [...]      Remove protection

Description:
  Manage Python virtual environments in the remote Google Drive
  environment. Environments are stored at @/venv/<name>/ and
  provide isolated PYTHONPATH for different projects.

Examples:
  GCS venv --create myproject            Create 'myproject' environment
  GCS venv --activate myproject          Activate 'myproject'
  GCS venv --list                        List all environments
  GCS venv --current                     Check current environment
  GCS venv --deactivate                  Return to base environment
  GCS venv --delete myproject            Delete 'myproject'
  GCS venv --protect production          Protect from accidental deletion

Related:
  GCS python --help                      Python execution
  GCS pip --help                         Package management""")
