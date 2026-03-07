"""MCP/CDP management commands for GCS.

Subcommands:
  boot            Launch debug Chrome, open .root.ipynb Colab tab
  shutdown        Close the debug Chrome instance
  status          Show CDP connectivity and configuration readiness
  setup-tutorial  Interactive tutorial for CDP-based automation setup

All Chrome/CDP interaction is isolated in helper modules for OS portability.
"""
import json
import os
import sys
import time
from pathlib import Path

_project_root = None

def _get_project_root():
    global _project_root
    if _project_root:
        return _project_root
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            _project_root = curr
            return curr
        curr = curr.parent
    _project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    return _project_root

if str(_get_project_root()) not in sys.path:
    sys.path.insert(0, str(_get_project_root()))

from logic.interface.config import get_color

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
YELLOW = get_color("YELLOW")
BLUE = get_color("BLUE")
RESET = get_color("RESET")

CDP_PORT = 9222
_DEFAULT_NOTEBOOK_NAME = ".root.ipynb"


def _get_notebook_name():
    cfg = _load_config()
    return cfg.get("root_notebook_name", _DEFAULT_NOTEBOOK_NAME)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _load_config():
    path = _get_project_root() / "data" / "config.json"
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def _save_config(cfg):
    path = _get_project_root() / "data" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------------------
# Chrome / CDP helpers (OS-portable)
# ---------------------------------------------------------------------------

def _get_debug_profile_dir():
    return os.path.expanduser("~/ChromeDebugProfile")


def _is_cdp_available(port=CDP_PORT):
    try:
        from logic.cdp.colab import is_chrome_cdp_available
        return is_chrome_cdp_available(port)
    except Exception:
        return False


def _find_chrome_debug_pid(port=CDP_PORT):
    """Find the PID of a Chrome process listening on the debug port."""
    import subprocess
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            return int(pids[0])
    except Exception:
        pass
    return None


def _launch_chrome_debug(port=CDP_PORT):
    """Launch Chrome with debugging port.

    Returns True if Chrome CDP becomes available within the timeout.
    """
    import subprocess
    profile_dir = _get_debug_profile_dir()

    if sys.platform == "darwin":
        chrome_app = "/Applications/Google Chrome.app"
        if not os.path.exists(chrome_app):
            return False
        subprocess.Popen([
            "open", "-na", "Google Chrome", "--args",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--remote-allow-origins=*"
        ])
    elif sys.platform.startswith("linux"):
        for binary in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
            import shutil
            if shutil.which(binary):
                subprocess.Popen([
                    binary,
                    f"--remote-debugging-port={port}",
                    f"--user-data-dir={profile_dir}",
                    "--remote-allow-origins=*"
                ])
                break
        else:
            return False
    elif sys.platform == "win32":
        chrome_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
        if not chrome_exe:
            return False
        subprocess.Popen([
            chrome_exe,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--remote-allow-origins=*"
        ])
    else:
        return False

    for _ in range(20):
        time.sleep(1)
        if _is_cdp_available(port):
            return True
    return False


def _get_chrome_launch_hint(port=CDP_PORT):
    """Return a platform-specific hint for manually launching Chrome."""
    profile_dir = _get_debug_profile_dir()
    if sys.platform == "darwin":
        return f'open -na "Google Chrome" --args --remote-debugging-port={port} --user-data-dir="{profile_dir}" --remote-allow-origins=*'
    elif sys.platform.startswith("linux"):
        return f'google-chrome --remote-debugging-port={port} --user-data-dir="{profile_dir}" --remote-allow-origins=*'
    elif sys.platform == "win32":
        return f'chrome.exe --remote-debugging-port={port} --user-data-dir="{profile_dir}" --remote-allow-origins=*'
    return f'chrome --remote-debugging-port={port} --user-data-dir="{profile_dir}" --remote-allow-origins=*'


def _shutdown_chrome_debug(port=CDP_PORT):
    """Close all tabs/windows in the debug Chrome via CDP, then terminate the process."""
    import urllib.request

    pid = _find_chrome_debug_pid(port)

    try:
        url = f"http://localhost:{port}/json/list"
        with urllib.request.urlopen(url, timeout=5) as resp:
            tabs = json.loads(resp.read().decode())

        version_url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(version_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        browser_ws = data.get("webSocketDebuggerUrl")
        if browser_ws:
            import websocket
            ws = websocket.create_connection(browser_ws, timeout=10)
            try:
                msg_id = 0
                for tab in tabs:
                    target_id = tab.get("id")
                    if target_id:
                        msg_id += 1
                        ws.send(json.dumps({
                            "id": msg_id,
                            "method": "Target.closeTarget",
                            "params": {"targetId": target_id}
                        }))
                msg_id += 1
                ws.send(json.dumps({"id": msg_id, "method": "Browser.close"}))
                ws.settimeout(3)
                try:
                    ws.recv()
                except Exception:
                    pass
            finally:
                ws.close()
    except Exception:
        pass

    if pid:
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    time.sleep(1)
    return not _is_cdp_available(port)


# ---------------------------------------------------------------------------
# Notebook helpers
# ---------------------------------------------------------------------------

def _find_or_create_notebook(cfg):
    """Locate .root.ipynb from config, or create it via CDP.

    Returns (file_id, colab_url, created).
    """
    env_folder_id = cfg.get("env_folder_id", "")
    root_folder_id = cfg.get("root_folder_id", "")
    target_folder = env_folder_id or root_folder_id
    existing_id = cfg.get("root_notebook_id", "")

    if not target_folder:
        return None, None, False

    if existing_id:
        colab_url = f"https://colab.research.google.com/drive/{existing_id}"
        return existing_id, colab_url, False

    try:
        from logic.cdp.colab import create_drive_file
        nb_name = cfg.get("root_notebook_name", _DEFAULT_NOTEBOOK_NAME)
        result = create_drive_file(nb_name, "colab", target_folder)
        if result.get("success"):
            file_id = result.get("id", result.get("file_id", ""))
            colab_url = result.get("link", result.get("colab_url",
                        f"https://colab.research.google.com/drive/{file_id}"))
            cfg["root_notebook_id"] = file_id
            cfg["root_notebook_url"] = colab_url
            _save_config(cfg)
            return file_id, colab_url, True
    except Exception:
        pass
    return None, None, False


def _open_colab_tab(colab_url, port=CDP_PORT):
    """Open the Colab notebook URL in a new Chrome tab via CDP."""
    try:
        import urllib.request
        from logic.cdp.colab import find_colab_tab

        existing = find_colab_tab(port)
        if existing and existing.get('url', ''):
            nb_id = colab_url.split('/drive/')[-1] if '/drive/' in colab_url else ''
            if nb_id and nb_id in existing['url']:
                return True

        version_url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(version_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        browser_ws = data.get("webSocketDebuggerUrl")
        if not browser_ws:
            return False

        import websocket
        ws = websocket.create_connection(browser_ws, timeout=15)
        try:
            ws.send(json.dumps({"id": 1, "method": "Target.createTarget", "params": {"url": colab_url}}))
            ws.settimeout(10)
            for _ in range(20):
                resp = json.loads(ws.recv())
                if resp.get("id") == 1:
                    return bool(resp.get("result", {}).get("targetId"))
        finally:
            ws.close()
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _drive_folder_url(folder_id):
    return f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else ""


def _colab_url(notebook_id):
    return f"https://colab.research.google.com/drive/{notebook_id}" if notebook_id else ""


# ---------------------------------------------------------------------------
# Public commands
# ---------------------------------------------------------------------------

def run_mcp_boot():
    """GCS --mcp boot: Launch debug Chrome and open .root.ipynb."""
    print(f"{BOLD}MCP Boot{RESET}: Initializing CDP-based Colab environment...")

    if _is_cdp_available():
        print(f"  {BOLD}Connected{RESET} to Chrome CDP on port {CDP_PORT}.")
    else:
        print(f"  Launching debug Chrome...")
        if _launch_chrome_debug():
            print(f"  {BOLD}Launched{RESET} Chrome with debug port {CDP_PORT}.")
        else:
            hint = _get_chrome_launch_hint()
            print(f"  {BOLD}{RED}Failed to launch{RESET} Chrome.")
            print(f"  Please run manually:\n    {hint}")
            return 1

    cfg = _load_config()
    file_id, colab_url, created = _find_or_create_notebook(cfg)

    if not file_id:
        has_folder = cfg.get("env_folder_id") or cfg.get("root_folder_id")
        if not has_folder:
            print(f"  {BOLD}{RED}Not configured{RESET}. Run {BOLD}GCS --setup-tutorial{RESET} first.")
        else:
            print(f"  {BOLD}{YELLOW}No notebook found{RESET}. Run {BOLD}GCS --mcp setup-tutorial{RESET} to create one.")
        return 1

    nb_name = _get_notebook_name()
    if created:
        print(f"  {BOLD}Created{RESET} {nb_name} via CDP.")
    else:
        print(f"  {BOLD}Found{RESET} {nb_name}.")

    print(f"  Opening Colab notebook...")
    if _open_colab_tab(colab_url):
        print(f"  {BOLD}Opened{RESET} Colab tab.")
    else:
        print(f"  {BOLD}{YELLOW}Could not open{RESET} tab automatically. URL: {colab_url}")

    time.sleep(2)
    from logic.cdp.colab import find_colab_tab
    tab = find_colab_tab()
    if tab:
        print(f"\n{BOLD}{GREEN}MCP Boot complete{RESET}. CDP ready for automated execution.")
        print(f"  {colab_url}")
    else:
        print(f"\n{BOLD}{YELLOW}MCP Boot partial{RESET}. Colab tab not yet detected (page may still be loading).")
        print(f"  {colab_url}")
    return 0


def run_mcp_shutdown():
    """GCS --mcp shutdown: Close the debug Chrome instance."""
    if not _is_cdp_available():
        print(f"{BOLD}MCP Shutdown{RESET}: Chrome CDP is not running.")
        return 0

    print(f"{BOLD}MCP Shutdown{RESET}: Closing debug Chrome...")
    if _shutdown_chrome_debug():
        print(f"  {BOLD}Closed{RESET} debug Chrome.")
        return 0
    else:
        print(f"  {BOLD}{YELLOW}Chrome may still be running{RESET}. Check manually.")
        return 1


def run_mcp_status():
    """GCS --mcp status: Show CDP readiness and config state."""
    cfg = _load_config()

    cdp_ok = _is_cdp_available()
    nb_id = cfg.get("root_notebook_id", "")
    env_id = cfg.get("env_folder_id", "")
    root_id = cfg.get("root_folder_id", "")

    print(f"{BOLD}MCP Status{RESET}:")
    print(f"  Chrome CDP:  {BOLD}{'Connected' + RESET if cdp_ok else RED + 'Not available' + RESET}")
    print(f"  Notebook:    {BOLD}{_colab_url(nb_id) + RESET if nb_id else YELLOW + 'Not configured' + RESET}")
    print(f"  Env Folder:  {BOLD}{_drive_folder_url(env_id) + RESET if env_id else YELLOW + 'Not configured' + RESET}")
    print(f"  Root Folder: {BOLD}{_drive_folder_url(root_id) + RESET if root_id else YELLOW + 'Not configured' + RESET}")

    if cdp_ok:
        from logic.cdp.colab import find_colab_tab
        tab = find_colab_tab()
        title = tab.get('title', 'unknown')[:50] if tab else None
        print(f"  Colab Tab:   {BOLD}{title + RESET if title else YELLOW + 'Not found' + RESET}")

    setup_done = bool(env_id or root_id)
    mcp_ready = cdp_ok and bool(nb_id)
    if not setup_done:
        print(f"\n  Run {BOLD}GCS --setup-tutorial{RESET} to configure Google Drive folders.")
    elif not nb_id:
        print(f"\n  Run {BOLD}GCS --mcp setup-tutorial{RESET} to create the notebook.")
    elif not cdp_ok:
        print(f"\n  Run {BOLD}GCS --mcp boot{RESET} to start Chrome CDP.")

    return 0 if mcp_ready else 1


def _get_translation(key, default, **kwargs):
    """Translation helper for CLI messages."""
    try:
        from logic.interface.lang import get_translation
        logic_dir = str(Path(__file__).resolve().parent.parent.parent)
        return get_translation(logic_dir, key, default, **kwargs)
    except Exception:
        text = default
        for k, v in kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))
        return text


def _make_step_callback():
    """Create a callback that prints step progress to terminal."""
    import sys as _sys
    def on_step_change(step_idx, total_steps, step_title):
        msg = f"{BOLD}{BLUE}{_get_translation('turing_user_completing', 'User completing')} {step_idx + 1}/{total_steps}{RESET}: {step_title}..."
        _sys.stdout.write(f"\r\033[K{msg}")
        _sys.stdout.flush()
    return on_step_change


def run_mcp_setup_tutorial():
    """GCS --mcp setup-tutorial: Launch the GUI-based MCP setup tutorial.

    Prerequisites: GCS --setup-tutorial should be completed first (folders configured).
    The tutorial guides through: Chrome detection, debug mode launch, notebook creation, trial run.
    """
    cfg = _load_config()
    env_id = cfg.get("env_folder_id", "")
    root_id = cfg.get("root_folder_id", "")

    if not (env_id or root_id):
        print(f"{BOLD}{RED}Not configured{RESET}. Google Drive folders are required.")
        print(f"  Run {BOLD}GCS --setup-tutorial{RESET} first, then re-run this command.")
        return 1

    import importlib.util
    tutorial_path = Path(__file__).resolve().parent.parent / "tutorial" / "mcp_setup" / "main.py"
    spec = importlib.util.spec_from_file_location("mcp_setup_tutorial", str(tutorial_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    result = mod.run_mcp_setup_tutorial(on_step_change=_make_step_callback())
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()
    if result and isinstance(result, dict) and result.get("status") == "success":
        print(f"{BOLD}{GREEN}Successfully completed{RESET} {_get_translation('mcp_tutorial_complete', 'MCP setup tutorial.')}")
        return 0
    elif result and isinstance(result, dict) and result.get("status") == "cancelled":
        print(f"{BOLD}{YELLOW}Cancelled{RESET} {_get_translation('mcp_tutorial_complete', 'MCP setup tutorial.')}")
        return 1
    else:
        reason = ""
        if result and isinstance(result, dict):
            reason = result.get('reason') or result.get('status') or ''
        if reason:
            print(f"{BOLD}Exited{RESET} MCP setup tutorial: {reason}")
        else:
            print(f"{BOLD}Exited{RESET} MCP setup tutorial.")
        return 0
