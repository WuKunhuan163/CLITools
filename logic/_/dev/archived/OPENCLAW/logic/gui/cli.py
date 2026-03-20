"""OPENCLAW CLI — Terminal-based agent interface.

Claude Code-inspired terminal UX with Turing machine progress states.
Combines interactive prompt, streaming agent output, and command execution
feedback in a single terminal session.

Usage:
    from tool.OPENCLAW.logic.gui.cli import OpenClawCLI
    cli = OpenClawCLI(session_mgr, backend="nvidia-glm-4-7b")
    cli.run()
"""
import sys
import os
import time
import threading
import shutil
from pathlib import Path
from typing import Optional

try:
    import readline  # noqa: F401 -- enables arrow keys/history in input()
except ImportError:
    pass

from interface.config import get_color
from logic._.lang.utils import get_translation
from logic.turing.display.manager import truncate_to_width, _get_configured_width
from interface.status import fmt_status, fmt_detail, fmt_stage
from tool.OPENCLAW.logic.session import SessionManager, Session

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent)


def _(key: str, default: str, **kwargs) -> str:
    return get_translation(_LOGIC_DIR, key, default, **kwargs)
from tool.OPENCLAW.logic.sandbox import (
    execute_command, get_project_summary,
    list_policies, set_command_policy, ALLOWED_COMMANDS, BLOCKED_COMMANDS,
)
from tool.OPENCLAW.logic.protocol import (
    build_system_prompt, build_task_message, build_feedback_message,
    parse_response_segments,
)
from tool.OPENCLAW.logic.guardrails import PipelineGuardrails

BOLD = get_color("BOLD")
DIM = get_color("DIM", "\033[2m")
GREEN = get_color("GREEN")
RED = get_color("RED")
BLUE = get_color("BLUE")
YELLOW = get_color("YELLOW")
CYAN = get_color("CYAN", "\033[36m")
MAGENTA = get_color("MAGENTA", "\033[35m")
RESET = get_color("RESET")

MAX_ITERATIONS = 50
_RUN_DIR = Path("/Applications/AITerminalTools/tool/OPENCLAW/data/run")

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "tmp"
_LOG_FILE = _LOG_DIR / "cli_debug.log"


def _dev_log(event: str, data: dict = None):
    """Append a structured JSON line to the dev debug log."""
    import json as _json
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event}
    if data:
        entry["data"] = data
    with open(_LOG_FILE, "a") as f:
        f.write(_json.dumps(entry, ensure_ascii=False, default=str) + "\n")




def _term_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def _hr(char="-", color=DIM):
    w = min(_term_width(), 100)
    return f"{color}{char * w}{RESET}"


def _truncate(text: str, max_lines: int = 20) -> str:
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    kept = lines[:max_lines]
    omitted = len(lines) - max_lines
    kept.append(f"{DIM}  ... ({omitted} more lines){RESET}")
    return "\n".join(kept)


def _box(label: str, content: str, color: str = CYAN) -> str:
    w = min(_term_width(), 100)
    top = f"{color}{BOLD}{label}{RESET}"
    border = f"{DIM}{'.' * (w - len(label) - 2)}{RESET}"
    return f"  {top} {border}\n{content}\n"


class _OutputTracker:
    """Transparent stdout wrapper that counts net visible lines.

    Tracks \\n (cursor down) and \\033[{n}A (cursor up) to calculate
    net vertical movement.  Works correctly with select_menu's
    ANSI clear/redraw cycles and _Spinner's \\r overwrites.
    """

    _CURSOR_UP_RE = __import__("re").compile(rb"\033\[(\d*)A")

    def __init__(self, wrapped):
        self._wrapped = wrapped
        self.lines = 0

    def write(self, s):
        self.lines += s.count("\n")
        for m in self._CURSOR_UP_RE.finditer(s.encode() if isinstance(s, str) else s):
            self.lines -= int(m.group(1) or b"1")
        return self._wrapped.write(s)

    def flush(self):
        return self._wrapped.flush()

    def __getattr__(self, name):
        return getattr(self._wrapped, name)


class _Spinner:
    """Inline spinning indicator for waiting states."""
    FRAMES = [".", "..", "...", "   "]

    def __init__(self, message: str, prefix: str = "  > "):
        self.message = message
        self._prefix = prefix
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame = 0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        while self._running:
            frame = self.FRAMES[self._frame % len(self.FRAMES)]
            line = f"{self._prefix}{BOLD}{BLUE}{self.message}{RESET}{frame}"
            w = _get_configured_width()
            if w > 0:
                line = truncate_to_width(line, w)
            sys.stdout.write(f"\r\033[K{line}")
            sys.stdout.flush()
            self._frame += 1
            time.sleep(0.4)

    def stop(self, final: str = ""):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        sys.stdout.write("\r\033[K")
        if final:
            w = _get_configured_width()
            out = truncate_to_width(f"{self._prefix}{final}", w) if w > 0 else f"{self._prefix}{final}"
            sys.stdout.write(f"{out}\n")
        sys.stdout.flush()


_CMD_REGISTRY = [
    ("/help",       "",                  "cmd_help_desc",       "Show this help."),
    ("/setup",      "",                  "cmd_setup_desc",      "Configure LLM provider and API key."),
    ("/models",     "",                  "cmd_models_desc",     "View and switch models."),
    ("/dashboard",  "",                  "cmd_dashboard_desc",  "Open LLM usage dashboard."),
    ("/sessions",   "",                  "cmd_sessions_desc",   "List all sessions."),
    ("/checkout",   "[<id>]",            "cmd_checkout_desc",   "Create or switch to a session."),
    ("/rename",     "<id> <title>",      "cmd_rename_desc",     "Rename a session."),
    ("/cleanup",    "",                  "cmd_cleanup_desc",    "Clear current session history."),
    ("/delete",     "[<id>]",            "cmd_delete_desc",     "Delete a session (current if no id)."),
    ("/sandbox",    "[<cmd> <policy>]",  "cmd_sandbox_desc",    "Manage sandbox command policies."),
    ("/status",     "",                  "cmd_status_desc",     "Show provider and session status."),
    ("/context",    "",                  "cmd_context_desc",    "Show current context token usage."),
    ("/log",        "[<step>]",          "cmd_log_desc",        "View session logs (list or open step)."),
    ("/gui",        "",                  "cmd_gui_desc",        "Open HTML GUI (web interface)."),
    ("/quit",       "",                  "cmd_quit_desc",       "Exit the CLI."),
]

_CMD_NAMES = [c[0] for c in _CMD_REGISTRY]


class OpenClawCLI:
    """Terminal-based OPENCLAW agent with Claude Code-style UX.

    Can be initialized with either a SessionManager (legacy) or an
    OpenClawCore instance. When using core, the CLI delegates state
    management to the shared core.
    """

    def __init__(self, session_mgr: SessionManager,
                 backend: str = "nvidia-glm-4-7b",
                 cdp_port: int = 9222,
                 temperature: float = 0.7,
                 max_tokens: int = 16384,
                 core=None):
        self._core = core
        self.session_mgr = core.session_mgr if core else session_mgr
        if core:
            self.backend = core.backend
        else:
            saved = self._load_saved_backend()
            if saved:
                self.backend = saved
            else:
                from tool.LLM.logic.registry import list_providers
                ready = [p for p in list_providers() if p["available"]]
                if len(ready) == 1:
                    self.backend = ready[0]["name"]
                    self._save_backend(self.backend)
                else:
                    self.backend = backend
        self.cdp_port = cdp_port
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.session: Optional[Session] = None
        self._provider = None
        self._context = None
        self._iteration = 0
        self._prompt_state = "idle"  # idle, running, done, error
        self._spinner: Optional[_Spinner] = None
        self._session_line: Optional[str] = None
        self._pending_cmds: list = []
        self._compression_trigger = core.compression_trigger if core else 0.5
        self._compression_target = core.compression_target if core else 0.1
        self._pid = os.getpid()
        self._state_file = _RUN_DIR / f"cli_{self._pid}.json"
        self._ctrl_file = _RUN_DIR / f"cli_{self._pid}.cmd"
        self._dashboard_server = None

    @staticmethod
    def _load_saved_backend() -> Optional[str]:
        from tool.LLM.logic.config import get_config_value
        from tool.LLM.logic.registry import _ALIASES
        name = get_config_value("active_backend")
        if name and name in _ALIASES:
            resolved = _ALIASES[name]
            from tool.LLM.logic.config import set_config_value
            set_config_value("active_backend", resolved)
            return resolved
        return name

    @staticmethod
    def _save_backend(name: str):
        from tool.LLM.logic.config import set_config_value
        set_config_value("active_backend", name)

    def _write_state(self, status: str, detail: str = ""):
        """Write current CLI state to the state file for external consumers."""
        import json as _json
        _RUN_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "pid": self._pid,
            "status": status,
            "detail": detail,
            "backend": self.backend,
            "session_id": self.session.id if self.session else None,
            "iteration": self._iteration,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        try:
            self._state_file.write_text(
                _json.dumps(state, ensure_ascii=False))
        except Exception:
            pass

    def _read_ctrl(self) -> Optional[str]:
        """Read and consume a pending control command, if any."""
        if not self._ctrl_file.exists():
            return None
        try:
            cmd = self._ctrl_file.read_text().strip()
            self._ctrl_file.unlink(missing_ok=True)
            return cmd if cmd else None
        except Exception:
            return None

    def _cleanup_run_files(self):
        """Remove state/control files on exit."""
        try:
            self._state_file.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            self._ctrl_file.unlink(missing_ok=True)
        except Exception:
            pass

    def _init_provider(self):
        from tool.LLM.logic.registry import get_provider
        try:
            self._provider = get_provider(self.backend)
        except ValueError:
            self._provider = None

    def _print_banner(self):
        os.system("clear")
        pid = os.getpid()
        print(f"{BOLD}OPENCLAW{RESET} {DIM}{_('banner_title', 'v2.0 [Agent CLI] PID {pid}', pid=pid)}{RESET}")
        print(f"  {DIM}{_('banner_setup', '/setup to configure')}{RESET}")
        print(f"  {DIM}{_('banner_help', '/help for commands')}{RESET}")
        print(f"  {DIM}{_('banner_quit', '/quit to exit')}{RESET}")

    def _print_help(self):
        max_sig = 0
        entries = []
        for name, args, tkey, default_desc in _CMD_REGISTRY:
            sig = f"{name} {args}".rstrip() if args else name
            max_sig = max(max_sig, len(sig))
            desc = _(tkey, default_desc)
            entries.append((sig, desc))
        pad = max_sig + 3
        for sig, desc in entries:
            print(f"  {DIM}{sig}{' ' * (pad - len(sig))}{desc}{RESET}")
        print(f"  {DIM}{_('anything_else_hint', 'Anything else is sent as a task to the agent.')}{RESET}")

    def _setup_llm(self):
        """Interactive LLM setup: (1) configure API key, (2) select active model.

        Esc at any step returns to the previous step.
        """
        from tool.LLM.logic.registry import list_providers
        from logic.turing.select import select_menu
        from tool.LLM.logic.providers.zhipu_glm4 import (
            get_api_key as get_zhipu_key, save_api_key as save_zhipu_key,
        )
        from tool.LLM.logic.providers.nvidia_glm47 import (
            get_api_key as get_nvidia_key, save_api_key as save_nvidia_key,
        )

        step = 1
        while step > 0:
            if step == 1:
                current_zhipu = get_zhipu_key()
                current_nvidia = get_nvidia_key()

                key_options = []
                detail_z = (current_zhipu[:8] + "..." + current_zhipu[-4:]
                            if current_zhipu and len(current_zhipu) > 12
                            else "configured" if current_zhipu else "not configured")
                key_options.append({"label": "Zhipu API Key", "value": "zhipu", "detail": detail_z})

                detail_n = (current_nvidia[:8] + "..." + current_nvidia[-4:]
                            if current_nvidia and len(current_nvidia) > 12
                            else "configured" if current_nvidia else "not configured")
                key_options.append({"label": "NVIDIA API Key", "value": "nvidia", "detail": detail_n})

                selected = select_menu(_("configure_api_key", "Configure API key:"), key_options)
                if not selected:
                    return

                url_map = {
                    "zhipu": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
                    "nvidia": "https://build.nvidia.com/z-ai/glm4_7",
                }
                save_map = {"zhipu": save_zhipu_key, "nvidia": save_nvidia_key}

                from logic.turing.select import read_masked
                current_key_map = {"zhipu": current_zhipu, "nvidia": current_nvidia}
                existing = current_key_map.get(selected["value"])

                print(f"    {DIM}{_('get_key_at', 'Get key at: {url}', url=url_map[selected['value']])}{RESET}")
                if existing:
                    masked = existing[:8] + "..." + existing[-4:] if len(existing) > 12 else existing
                    label = _("enter_api_key_label", "Enter API key")
                    hint = _("keep_current_key_hint",
                             "(enter to use current key {current_key})",
                             current_key=masked)
                    api_key = read_masked(
                        f"{BOLD}{label}{RESET} {DIM}{hint}{RESET}:",
                        allow_empty=True)
                else:
                    api_key = read_masked(
                        f"{BOLD}{_('enter_api_key_label', 'Enter API key')}{RESET}:")

                if api_key is None:
                    from logic.turing.select import erase_lines
                    erase_lines(3)  # confirmation + URL hint + API key prompt
                    step = 1
                    continue

                if api_key:
                    save_map[selected["value"]](api_key)
                    print(fmt_status(_('saved', 'Saved.')))
                elif existing:
                    print(f"  {DIM}{_('using_stored_key', 'Using stored API key.')}{RESET}")
                else:
                    continue
                step = 2

            elif step == 2:
                providers = list_providers()
                ready = [p for p in providers if p["available"]]
                if not ready:
                    print(f"  {DIM}{_('no_providers_ready', 'No providers ready. Configure an API key first.')}{RESET}")
                    step = 1
                    continue
                if len(ready) == 1:
                    self.backend = ready[0]["name"]
                    self._save_backend(self.backend)
                    self._init_provider()
                    print(fmt_status(_('active_model_prefix', 'Active model:'),
                                      complement=ready[0]['name'],
                                      dim=f"({ready[0]['model']})"))
                    return

                model_options = []
                for p in ready:
                    model_options.append({
                        "label": f"{p['name']} ({p['model']})",
                        "value": p["name"],
                        "detail": f"{p.get('rpm_limit', '?')} RPM, {p.get('max_context', '?'):,} ctx",
                    })
                chosen = select_menu(_("select_active_model", "Select active model:"), model_options)
                if not chosen:
                    step = 1
                    continue
                self.backend = chosen["value"]
                self._save_backend(self.backend)
                self._init_provider()
                print(fmt_status(_('switched_to_prefix', 'Switched to'),
                                  complement=f"{chosen['value']}."))
                return

    _IDLE = "\u25A1"    # □
    _ACTIVE = "\u25A0"  # ■

    def _prompt(self) -> str:
        """Show idle prompt and wait for user input or injected command.

        Uses the multiline_input widget: Enter for new line, Ctrl+D
        to submit.  Periodically checks the control file for injection.
        """
        try:
            from logic.turing.multiline_input import multiline_input
            text = multiline_input(
                prompt=f"\n{self._IDLE} ",
                continuation="\u2551 ",
                placeholder=_("input_placeholder",
                              "Type here, Ctrl+D to submit."),
                submit_color=CYAN,
                inject_check=self._read_ctrl,
            )
            return text
        except Exception:
            return self._prompt_fallback()

    def _prompt_fallback(self) -> str:
        """Fallback prompt without multiline support."""
        sys.stdout.write(f"\n{self._IDLE} ")
        sys.stdout.flush()
        try:
            import select
            while True:
                ctrl = self._read_ctrl()
                if ctrl:
                    sys.stdout.write(f"{ctrl}\n")
                    sys.stdout.flush()
                    return ctrl
                ready, _, _ = select.select([sys.stdin], [], [], 0.5)
                if ready:
                    line = sys.stdin.readline()
                    if not line:
                        return "/quit"
                    return line.rstrip("\n")
        except (EOFError, OSError):
            return "/quit"
        except KeyboardInterrupt:
            print()
            return "/quit"

    def _mark_running(self, text: str):
        """Rewrite the prompt line(s) to show ■ (default, running)."""
        self._rewrite_submitted(text, "")

    def _mark_done(self, text: str):
        """Rewrite the prompt line(s) to show ■ (green, done)."""
        self._rewrite_submitted(text, GREEN)

    def _mark_failed(self, text: str):
        """Rewrite the prompt line(s) to show ■ (red, failed)."""
        self._rewrite_submitted(text, RED)

    _CONT_RUN = "\u2503"  # ┃ heavy vertical for running state

    def _rewrite_submitted(self, text: str, indicator_color: str):
        """Rewrite all lines of submitted text with ■/┃ indicators.

        indicator_color controls the color of ■/┃ (empty = default).
        Text content is always rendered in command blue (CYAN).
        """
        sys.stdout.flush()
        text_lines = text.split('\n')
        n = len(text_lines)
        sys.stdout.write(f"\033[{n}A")
        for i, line in enumerate(text_lines):
            indicator = self._ACTIVE if i == 0 else self._CONT_RUN
            if indicator_color:
                ind = f"{indicator_color}{indicator}{RESET} "
            else:
                ind = f"{indicator} "
            sys.stdout.write(f"\033[K{ind}{CYAN}{line}{RESET}\n")
        sys.stdout.flush()

    def _recolor_indicator(self, text: str, lines_below: int, color: str):
        """Rewrite the indicator line(s) from a distance, then return cursor.

        Indicators (■/┃) get the status color; text stays in command blue.
        """
        text_lines = text.split('\n')
        n = len(text_lines)
        up = lines_below + n
        sys.stdout.write(f"\033[{up}A")
        for i, line in enumerate(text_lines):
            indicator = self._ACTIVE if i == 0 else self._CONT_RUN
            sys.stdout.write(f"\033[K{color}{indicator}{RESET} {CYAN}{line}{RESET}\n")
        if lines_below > 0:
            sys.stdout.write(f"\033[{lines_below}B")
        sys.stdout.flush()

    def _show_sessions(self):
        sessions = self.session_mgr.list_sessions()
        if not sessions:
            print(f"  {DIM}{_('no_sessions', 'No sessions.')}{RESET}")
            return
        current_id = self.session.id if self.session else None
        for i, s in enumerate(sessions):
            title = s.get_display_title()
            if len(title) > 40:
                title = title[:37] + "..."
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s.updated_at))
            marker = " *" if s.id == current_id else ""
            print(f"  {DIM}{i}:{RESET} {CYAN}{s.id}{RESET}  {title}  {DIM}[{ts}]{RESET}{BOLD}{marker}{RESET}")

    def _cleanup_session(self):
        """Clear current session with user confirmation."""
        if not self.session:
            print(f"  {DIM}{_('no_active_session', 'No active session.')}{RESET}")
            return
        from logic.turing.select import select_horizontal
        sid = self.session.id
        msgs = len(self.session.messages)
        print(f"  {DIM}{_('session_info', 'Session {sid} ({msgs} messages)', sid=sid, msgs=msgs)}{RESET}")
        choice = select_horizontal(
            _("clear_session_prompt", "Clear session history?"),
            ["Yes", "No"],
            default_index=1,
        )
        if choice == 0:
            self.session = None
            self._context = None
            self._iteration = 0
            self._session_line = None
            print(fmt_status(_('cleared', 'Cleared.')))
        else:
            print(f"  {DIM}{_('cancelled', 'Cancelled.')}{RESET}")

    def _checkout_session(self, target_id: str = ""):
        """Create a new session or switch to an existing one."""
        if target_id:
            s = self.session_mgr.get_session(target_id)
            if not s:
                print(fmt_status(_('session_not_found_label', 'Session not found.'), dim=target_id))
                return
            if self.session:
                print(f"  {DIM}{_('leaving_session', 'Leaving session {sid}.', sid=self.session.id)}{RESET}")
            self.session = s
            self._context = None
            self._iteration = 0
            self._session_line = None
            print(fmt_status(_('switched_to_session_label', 'Switched.'),
                              dim=f"{s.id[:8]}: {s.get_display_title()}"))
        else:
            if self.session:
                print(f"  {DIM}{_('leaving_session', 'Leaving session {sid}.', sid=self.session.id)}{RESET}")
            self.session = None
            self._context = None
            self._iteration = 0
            self._session_line = None
            self.session = self.session_mgr.create_session()
            print(fmt_status(_('new_session_label', 'New session.'), dim=self.session.id[:8]))

    def _delete_current_session(self):
        """Delete current session and switch to the most recent one."""
        if not self.session:
            print(f"  {DIM}{_('no_active_session', 'No active session.')}{RESET}")
            return
        self._delete_session(self.session.id)

    def _delete_session(self, target_id: str):
        """Delete a session with user confirmation."""
        from logic.turing.select import select_horizontal
        s = self.session_mgr.get_session(target_id)
        if not s:
            print(fmt_status(_('session_not_found_label', 'Session not found.'), dim=target_id))
            return
        msgs = len(s.messages)
        title = s.get_display_title()
        print(f"  {DIM}{title} ({msgs} {_('session_info', 'messages')}){RESET}")
        choice = select_horizontal(
            _("delete_session_prompt", "Delete this session?"),
            ["Yes", "No"],
            default_index=1,
        )
        if choice == 0:
            is_current = self.session and self.session.id == target_id
            self.session_mgr.delete_session(target_id)
            if is_current:
                self.session = None
                self._context = None
                self._iteration = 0
                self._session_line = None
                remaining = self.session_mgr.list_sessions()
                if remaining:
                    self.session = remaining[0]
                    print(fmt_status(_('deleted', 'Deleted.'),
                                      complement=_('switched_to_session_label', 'Switched.'),
                                      dim=self.session.id[:8]))
                else:
                    print(fmt_status(_('deleted', 'Deleted.')))
            else:
                print(fmt_status(_('deleted', 'Deleted.')))
        else:
            print(f"  {DIM}{_('cancelled', 'Cancelled.')}{RESET}")

    def _rename_session(self, args: str):
        """Rename a session: /rename <id> <new title>."""
        parts = args.split(None, 1)
        if len(parts) < 2:
            print(f"  {DIM}{_('rename_usage', 'Usage: /rename <session-id> <new title>')}{RESET}")
            return
        sid, new_title = parts[0], parts[1]
        s = self.session_mgr.get_session(sid)
        if not s:
            print(fmt_status(_('session_not_found_label', 'Session not found.'), dim=sid))
            return
        self.session_mgr.update_title(sid, new_title)
        print(fmt_status(_('renamed_label', 'Renamed.'), dim=f"{sid[:8]}: {new_title}"))

    def _show_models(self):
        """Show all models with config status, allow switching."""
        from tool.LLM.logic.registry import list_providers
        from logic.turing.select import select_menu

        providers = list_providers()
        ready = [p for p in providers if p["available"]]

        print(fmt_status(_('models_label', 'Models'),
                          dim=f"({len(providers)} registered, {len(ready)} configured)"))
        for p in providers:
            name = p["name"]
            model = p.get("model", "?")
            active = " *" if name == self.backend else ""
            if p["available"]:
                print(f"    {GREEN}{name}{RESET} ({model}){BOLD}{active}{RESET}")
            else:
                print(f"    {DIM}{name} ({model}) -- {_('not_configured', 'not configured')}{RESET}")

        if len(ready) <= 1:
            return

        options = []
        for p in ready:
            active = " (active)" if p["name"] == self.backend else ""
            options.append({
                "label": f"{p['name']} ({p.get('model', '?')}){active}",
                "value": p["name"],
            })
        chosen = select_menu(_("switch_model", "Switch model:"), options)
        if chosen and chosen["value"] != self.backend:
            self.backend = chosen["value"]
            self._save_backend(self.backend)
            self._init_provider()
            self._context = None
            print(fmt_status(_('switched_to_prefix', 'Switched to'), complement=f"{self.backend}."))

    def _manage_sandbox(self, direct_cmd: str = "", direct_policy: str = ""):
        """Interactive sandbox policy manager.

        No args: full interactive editor (up/down to select, left/right to toggle).
        With args: directly set a command's policy.
        """
        from logic.turing.select import _read_key

        if direct_cmd:
            if direct_policy not in ("allow", "deny", "remove"):
                print(fmt_status(_('sandbox_invalid_policy_label', 'Invalid policy.'),
                                  complement=_('sandbox_invalid_policy_hint', 'Use: allow, deny, remove.'),
                                  style="error"))
                return
            if direct_policy == "remove":
                from tool.OPENCLAW.logic.sandbox import remove_command_policy
                removed = remove_command_policy(direct_cmd)
                if removed:
                    print(fmt_status(_('sandbox_removed_label', 'Removed.'), dim=direct_cmd))
                else:
                    print(f"  {DIM}{_('sandbox_no_policy', 'No policy set for {cmd}.', cmd=direct_cmd)}{RESET}")
            else:
                set_command_policy(direct_cmd, direct_policy)
                print(fmt_status(_('sandbox_set_label', 'Set.'), dim=f"{direct_cmd} = {direct_policy}"))
            return

        policies = list_policies()
        if not policies:
            print(f"  {DIM}{_('sandbox_no_policies', 'No user-configured sandbox policies.')}{RESET}")
            print(f"  {DIM}{_('sandbox_auto_create', 'Policies are created when the agent runs unknown commands.')}{RESET}")
            print(f"  {DIM}{_('sandbox_manual', 'Set manually: /sandbox <command> allow|deny')}{RESET}")
            return

        entries = sorted(policies.items())
        policy_cycle = ["allow", "deny"]
        cursor = 0
        num_lines = len(entries) + 2

        def _render():
            sys.stdout.write(f"  {BOLD}{_('sandbox_label', 'Sandbox Policies')}{RESET} {DIM}(arrows to navigate, Enter to confirm, Esc to exit){RESET}\n")
            for i, (cmd, pol) in enumerate(entries):
                if pol == "allow":
                    pol_str = f"{GREEN}{BOLD}allow{RESET}"
                else:
                    pol_str = f"{RED}{BOLD}deny{RESET}"
                if i == cursor:
                    sys.stdout.write(f"    {CYAN}>{RESET} {BOLD}{cmd:<20}{RESET} [{pol_str}]\n")
                else:
                    sys.stdout.write(f"      {cmd:<20} [{pol_str}]\n")
            sys.stdout.write(f"  {DIM}{_('sandbox_builtin', 'Built-in: {allowed} allowed, {blocked} blocked', allowed=len(ALLOWED_COMMANDS), blocked=len(BLOCKED_COMMANDS))}{RESET}\n")
            sys.stdout.flush()

        def _clear():
            for _ in range(num_lines):
                sys.stdout.write("\033[A\033[K")
            sys.stdout.flush()

        if not sys.stdin.isatty():
            _render()
            return

        from interface.turing import get_global_suppressor
        suppressor = get_global_suppressor()
        suppressor.start()

        try:
            _render()
            changed = False
            while True:
                key = _read_key()
                if key == "up":
                    cursor = (cursor - 1) % len(entries)
                elif key == "down":
                    cursor = (cursor + 1) % len(entries)
                elif key in ("left", "right"):
                    cmd_name, cur_pol = entries[cursor]
                    idx = policy_cycle.index(cur_pol) if cur_pol in policy_cycle else 0
                    if key == "right":
                        idx = (idx + 1) % len(policy_cycle)
                    else:
                        idx = (idx - 1) % len(policy_cycle)
                    new_pol = policy_cycle[idx]
                    entries[cursor] = (cmd_name, new_pol)
                    changed = True
                elif key == "enter":
                    _clear()
                    if changed:
                        for cmd_name, pol in entries:
                            set_command_policy(cmd_name, pol)
                        print(fmt_status(_('saved', 'Saved.'), dim=f"{len(entries)} policies"))
                    else:
                        print(f"  {DIM}{_('no_changes', 'No changes.')}{RESET}")
                    return
                elif key in ("esc", "ctrl-c"):
                    _clear()
                    print(f"  {DIM}{_('cancelled', 'Cancelled.')}{RESET}")
                    return
                else:
                    continue
                _clear()
                _render()
        finally:
            suppressor.stop()

    def _show_status(self):
        print(fmt_status(_('status_title', 'Status')))
        if self._provider:
            info = self._provider.get_info()
            avail = f"{GREEN}available{RESET}" if info["available"] else f"{RED}not configured{RESET}"
            print(f"    Provider: {info['model']} ({avail})")
            print(f"    RPM: {info['rpm_limit']}  |  Max context: {info['max_context']:,} tokens")
        if self.session:
            print(f"    Session: {self.session.id} ({self.session.status})")
            print(f"    Messages: {len(self.session.messages)}")
        if self._context:
            msgs = self._context.get_messages_for_api()
            est_tokens = sum(len(m.get("content", "")) // 4 for m in msgs)
            print(f"    Context: ~{est_tokens:,} tokens (estimated)")

    def _launch_dashboard(self):
        """Launch the LLM dashboard as a persistent local server."""
        from tool.LLM.logic.dashboard.generate import generate
        from logic.serve.html_server import LocalHTMLServer

        path = generate()
        server = LocalHTMLServer(
            html_path=path,
            port=0,
            title="LLM Dashboard",
            on_generate=lambda p: generate(output_path=p),
        )
        server.start()
        print(fmt_status(_('saved', 'Saved.'), dim=server.url))
        server.open_browser()
        self._dashboard_server = server

    def _launch_html_gui(self):
        """Launch the OPENCLAW HTML chat GUI in a browser."""
        from tool.OPENCLAW.logic.gui.chat_html import OpenClawChatHTML

        html_gui = OpenClawChatHTML(
            session_mgr=self.session_mgr,
            backend=self.backend,
        )
        html_gui.server = None
        from logic._.gui.html.blueprint.chatbot.server import ChatbotServer
        server = ChatbotServer(
            title="OPENCLAW",
            on_send=html_gui._on_send,
            session_provider=self.session_mgr,
        )
        html_gui.server = server
        server.start()
        server.open_browser()
        print(fmt_status("GUI", dim=f"http://localhost:{server.port}/"))
        self._html_gui = html_gui

    def _show_context_usage(self):
        if not self._context:
            print(f"  {DIM}{_('no_active_context', 'No active context.')}{RESET}")
            return
        msgs = self._context.get_messages_for_api()
        print(fmt_status(_('context_title', 'Context')))
        for m in msgs:
            role = m["role"]
            length = len(m.get("content", ""))
            preview = m.get("content", "")[:60].replace("\n", " ")
            role_color = GREEN if role == "assistant" else CYAN if role == "user" else DIM
            print(f"    {role_color}{role:>10}{RESET}  {length:>6} chars  {DIM}{preview}...{RESET}")

    def _show_log(self, step_arg: str = ""):
        """List or open session operation logs.

        No arg → list all logs for the current session.
        Integer arg → open that step's log file with the system viewer.
        """
        import subprocess

        if not self.session:
            print(f"  {DIM}{_('no_active_session', 'No active session.')}{RESET}")
            return

        log_dir = self.session_mgr.data_dir / self.session.id / "logs"
        if not log_dir.exists():
            print(f"  {DIM}{_('log_no_logs', 'No logs yet.')}{RESET}")
            return

        logs = sorted(log_dir.glob("*.log.md"), key=lambda p: p.name)

        if not step_arg:
            print(fmt_status(_('log_title', 'Logs for session {sid}', sid=self.session.id[:8])))
            for lf in logs:
                size = lf.stat().st_size
                ts = time.strftime("%H:%M:%S", time.localtime(lf.stat().st_mtime))
                print(f"    {DIM}{lf.stem}  {size} bytes  {ts}{RESET}")
            if not logs:
                print(f"    {DIM}{_('log_no_logs', 'No logs yet.')}{RESET}")
            return

        target_name = f"s{step_arg}.log.md"
        target = log_dir / target_name
        if not target.exists():
            print(f"  {RED}{_('log_not_found', 'Log not found: {name}', name=target_name)}{RESET}")
            return

        print(f"  {DIM}{_('log_opening', 'Opening {path}...', path=str(target))}{RESET}")
        try:
            subprocess.Popen(["open", str(target)],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            subprocess.Popen(["xdg-open", str(target)],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)

    def _ensure_session(self):
        if not self.session:
            label = _("starting_session", "Starting session...")
            sys.stdout.write(self._stage(label, "active") + "\n")
            sys.stdout.flush()
            self.session = self.session_mgr.create_session()
            sid_short = self.session.id[:8]
            done_label = _("session_started_label", "Session started")
            done_detail = _("session_started_detail",
                            "Session {sid} is ready.", sid=sid_short)
            self._session_line_label = done_label
            self._session_line_desc = done_detail
            sys.stdout.write(
                f"\033[A\033[K{self._stage(done_label, 'done', desc=done_detail)}\n")
            sys.stdout.flush()
            print(self._detail(
                _("session_id_full", "ID: {sid}", sid=self.session.id)))

    def _recolor_session_line(self):
        """Recolor the 'Started session' line to green after pipeline success."""
        label = getattr(self, '_session_line_label', None)
        if not label:
            return
        tracker = sys.stdout
        if isinstance(tracker, _OutputTracker):
            n = tracker.lines
        else:
            return
        if n < 1:
            return
        desc = getattr(self, '_session_line_desc', '')
        colored = self._stage(label, "done", desc=desc)
        raw = tracker._wrapped
        raw.write(f"\033[{n}A\033[K{colored}\n")
        if n > 1:
            raw.write(f"\033[{n - 1}B")
        raw.flush()

    # Hierarchical Turing machine indicators
    _L1 = ">"       # Level 1: main agent
    _L2 = "\u2981"  # ⦁ Level 2: subagent
    _L1_PFX = "  > "   # 4 chars: major operation prefix
    _L2_PFX = "    \u2981 "  # 6 chars: subagent prefix
    _DETAIL = "    "   # 4 chars: detail indent (same width as L1)

    def _stage(self, label: str, status: str = "active",
               desc: str = "", depth: int = 1) -> str:
        """Format a major operation line: ``> {label} {desc}``.

        Delegates to :func:`logic.turing.status.fmt_stage`.
        """
        return fmt_stage(label, desc=desc, status=status, depth=depth)

    def _detail(self, text: str, depth: int = 1, styled: bool = False) -> str:
        """Format a detail/sub-info line, aligned under parent.

        Delegates to :func:`logic.turing.status.fmt_detail`.
        """
        indent_n = 6 if depth == 2 else 4
        return fmt_detail(text, indent=indent_n, styled=styled)

    def _thought(self, text: str) -> str:
        """Format an agent thought/reasoning line (dimmed, >-prefixed)."""
        return truncate_to_width(
            f"    {DIM}> {text}{RESET}", _get_configured_width())

    def _thought_cont(self, text: str) -> str:
        """Format a continuation line of agent thought (dimmed, |-prefixed)."""
        return truncate_to_width(
            f"    {DIM}| {text}{RESET}", _get_configured_width())

    def _tool_call(self, text: str, log_ref: str = "") -> str:
        """Format a tool call line (bullet, with optional log reference)."""
        ref = f" {DIM}[{log_ref}]{RESET}" if log_ref else ""
        return truncate_to_width(
            f"    {BOLD}*{RESET} {text}{ref}", _get_configured_width())

    def _run_pipeline(self, user_task: str) -> bool:
        """Run the agent pipeline. Returns True on success, False on error."""
        from tool.LLM.logic.session_context import SessionContext

        self._ensure_session()
        self.session_mgr.add_message(self.session.id, "user", user_task)

        guardrails = PipelineGuardrails()

        if self._context is None:
            project_summary = get_project_summary()
            system_prompt = build_system_prompt(project_summary)
            self._context = SessionContext(
                system_prompt=system_prompt,
                max_context_tokens=32000,
            )
            _dev_log("context_init", {
                "session_id": self.session.id,
                "system_prompt_len": len(system_prompt),
                "project_summary_len": len(project_summary),
            })

        task_msg = build_task_message(user_task)
        self._context.add_user(task_msg)

        while self._iteration < MAX_ITERATIONS:
            self._iteration += 1

            op_log = self.session_mgr.create_log(
                self.session.id, self._iteration)
            messages = self._context.get_messages_for_api()
            op_log.write_messages(messages)
            op_log.write("Parameters", {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "backend": self.backend,
                "step": self._iteration,
            })

            _dev_log("llm_request", {
                "step": self._iteration,
                "message_count": len(messages),
                "log_file": op_log.filename,
            })

            req_label = _("preparing_request_label", "Preparing request")
            req_desc = _("preparing_request_desc",
                         "Sending to {backend} (step {step})... [{ref}]",
                         backend=self.backend, step=self._iteration,
                         ref=op_log.ref)
            print(self._stage(req_label, "active", desc=req_desc))

            # DEV BREAKPOINT: log bootstrap before first send
            import json as _bp_json
            bp_path = _LOG_DIR / "bootstrap_dump.json"
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(bp_path, "w") as _bp_f:
                _bp_json.dump({
                    "step": self._iteration,
                    "message_count": len(messages),
                    "messages": [
                        {"role": m.get("role", "?"),
                         "content_len": len(m.get("content", "")),
                         "content_head": m.get("content", "")[:2000]}
                        for m in messages
                    ],
                    "backend": self.backend,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }, _bp_f, ensure_ascii=False, indent=2)
            print(self._detail(
                _('breakpoint_msg', '[BREAKPOINT] Bootstrap state written to log.')
                + f" {bp_path}"))

            # Guardrail: step + duration limits
            step_err = guardrails.check_step_limit()
            if step_err:
                print(self._detail(f"{YELLOW}{step_err}{RESET}", styled=True))
                return False
            dur_err = guardrails.check_duration()
            if dur_err:
                print(self._detail(f"{YELLOW}{dur_err}{RESET}", styled=True))
                return False

            spinner = _Spinner(
                _("thinking", "Thinking (step {step})", step=self._iteration), prefix=self._DETAIL)
            self._spinner = spinner
            spinner.start()

            try:
                result = self._provider.send(
                    messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as e:
                spinner.stop(f"{RED}{_('api_error', 'API error: {error}', error=e)}{RESET}")
                _dev_log("llm_error", {"step": self._iteration, "error": str(e)})
                return False

            if not result.get("ok"):
                error = result.get("error", "Unknown error")
                if "429" in str(error):
                    spinner.stop(f"{YELLOW}{_('rate_limited', 'Rate limited. Waiting 60s...')}{RESET}")
                    _dev_log("rate_limited", {"step": self._iteration})
                    time.sleep(60)
                    continue
                spinner.stop(f"{RED}{_('error_prefix', 'Error: {error}', error=error)}{RESET}")
                _dev_log("llm_error", {"step": self._iteration, "error": error})
                return False

            response_text = result.get("text", "")
            usage = result.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            token_info = f" {DIM}({tokens_used} tokens){RESET}" if tokens_used else ""
            spinner.stop(f"{GREEN}{_('response_received', 'Response received.')}{RESET}{token_info}")

            _dev_log("llm_response", {
                "step": self._iteration,
                "tokens": tokens_used,
                "response_len": len(response_text),
                "response_head": response_text[:200],
            })

            # Guardrail: token budget
            token_err = guardrails.check_token_budget(tokens_used)
            if token_err:
                print(self._detail(f"{YELLOW}{token_err}{RESET}", styled=True))
                return False

            # Guardrail: response validation
            validate_err = guardrails.validate_response(response_text)
            if validate_err:
                print(self._detail(f"{YELLOW}{validate_err}{RESET}", styled=True))
                return False

            self._context.add_assistant(response_text)

            # Guardrail: loop detection
            loop_correction = guardrails.check_loop(response_text)
            if loop_correction:
                print(self._detail(f"{YELLOW}{_('agent_loop', 'Agent stuck in loop. Injecting correction...')}{RESET}", styled=True))
                self._context.add_user(loop_correction)
                continue

            seg_parsed = parse_response_segments(response_text)
            segments = seg_parsed["segments"]
            task_complete = seg_parsed["task_complete"]
            step_complete = seg_parsed["step_complete"]
            step_summary = seg_parsed.get("step_summary")
            parsed_title = seg_parsed.get("title")

            op_log.write("Agent response", {
                "response_text": response_text[:4000],
                "segments": len(segments),
                "task_complete": task_complete,
                "step_complete": step_complete,
                "step_summary": step_summary,
            })

            # Also get flat command list for guardrail counting
            all_commands = [s["content"] for s in segments if s["type"] == "command"]

            # Robustness: if agent omitted step completion token but issued commands,
            # treat as implicit step_complete (smaller models may forget tokens)
            if all_commands and not step_complete and not task_complete:
                step_complete = True

            # Auto-title on first response
            if self._iteration == 1:
                title = parsed_title or user_task[:50].strip().split("\n")[0]
                if title:
                    self.session_mgr.update_title(self.session.id, title)

            # Guardrail: command count limit
            if all_commands:
                cmd_err = guardrails.check_command_limit(len(all_commands))
                if cmd_err:
                    print(self._detail(f"{YELLOW}{cmd_err}{RESET}", styled=True))
                    return False

            # Update "Thinking..." to step summary if agent provided one
            if step_summary:
                sys.stdout.write(f"\033[A\033[K")
                print(self._stage(step_summary, "active"))

            # Display segments in order: thought → > block, command → • bullet
            feedback_parts = []
            cmd_idx = 0
            for seg in segments:
                if seg["type"] == "step_summary":
                    pass  # already handled above
                elif seg["type"] == "thought":
                    lines = [l.strip() for l in seg["content"].split("\n") if l.strip()]
                    if lines:
                        print(self._thought(lines[0]))
                        for extra in lines[1:]:
                            print(self._thought_cont(extra))
                elif seg["type"] == "experience":
                    print(self._stage(_("experience_label", "Experience: {exp}", exp=seg['content']), "done"))
                    self.session_mgr.add_message(
                        self.session.id, "system", f"[Experience] {seg['content']}")
                elif seg["type"] == "command":
                    cmd_idx += 1
                    cmd = seg["content"]
                    cmd_label = f"Exec {cmd_idx}/{len(all_commands)}"
                    cmd_desc = cmd
                    log_ref = op_log.ref if hasattr(op_log, 'ref') else ""
                    print(self._tool_call(cmd, log_ref=log_ref))
                    print(self._stage(cmd_label, "active", desc=cmd_desc))
                    exec_tracker = _OutputTracker(sys.stdout)
                    sys.stdout = exec_tracker

                    exec_spinner = _Spinner(_("running", "Running"), prefix=self._DETAIL)
                    self._spinner = exec_spinner
                    exec_spinner.start()

                    cmd_result = execute_command(cmd)
                    _dev_log("exec", {
                        "step": self._iteration,
                        "cmd": cmd,
                        "ok": cmd_result.get("ok"),
                        "exit_code": cmd_result.get("exit_code"),
                        "output_len": len(cmd_result.get("output", "")),
                    })

                    op_log.write(f"Command: {cmd}", {
                        "ok": cmd_result.get("ok"),
                        "exit_code": cmd_result.get("exit_code"),
                        "output": cmd_result.get("output", "")[:2000],
                        "error": cmd_result.get("error", "")[:500],
                    })

                    cmd_ok = cmd_result.get("ok", False)
                    if cmd_ok:
                        exec_spinner.stop(
                            f"{GREEN}{_('exec_completed', 'Completed (exit {code}).', code=cmd_result.get('exit_code', 0))}{RESET}")
                        output = cmd_result.get("output", "")
                        if output:
                            truncated = _truncate(output, 15)
                            for line in truncated.split("\n"):
                                print(self._detail(line))
                        if "--openclaw-write-file" in cmd:
                            guardrails.record_write(cmd)
                    else:
                        error = cmd_result.get("error", "")
                        brief = error.split("\n")[0][:120] if error else ""
                        fail_msg = f"{RED}{_('exec_failed', 'Failed.')}{RESET} {brief}" if brief else f"{RED}{_('exec_failed', 'Failed.')}{RESET}"
                        exec_spinner.stop(fail_msg)
                        guardrails.record_command_failure()

                    sys.stdout = exec_tracker._wrapped
                    recolor_status = "done" if cmd_ok else "error"
                    n = exec_tracker.lines
                    if n > 0:
                        recolored = self._stage(cmd_label, recolor_status, desc=cmd_desc)
                        sys.stdout.write(
                            f"\033[{n + 1}A\033[K{recolored}\n"
                            f"\033[{n}B")
                        sys.stdout.flush()

                    self.session_mgr.add_message(
                        self.session.id, "system", f"[Exec] {cmd}")
                    feedback = build_feedback_message(cmd, cmd_result)
                    feedback_parts.append(feedback)

            # Check task completion
            if task_complete:
                step_label = step_summary or _("task_finished", "Task finished.")
                print(self._stage(step_label, "done"))
                self.session_mgr.complete_session(self.session.id)
                self._context = None
                self._iteration = 0
                return True

            # Step complete: mark current step as done, continue to next
            if step_complete and step_summary:
                print(self._stage(step_summary, "done"))

            if not feedback_parts:
                if step_complete:
                    pass  # will loop to next iteration with auto-feedback
                else:
                    return True

            all_feedback = "\n\n".join(feedback_parts)

            # Active skill chaining: inject relevant skills on error
            " ".join(
                f.split("\n")[0] for f in feedback_parts
                if "[Command FAILED]" in f
            )
            all_feedback += (
                "\n\nContinue with the task. Start with <<STEP: label >>. "
                "End with <<OPENCLAW_STEP_COMPLETE>> or "
                "<<OPENCLAW_TASK_COMPLETE>> when fully done."
            )
            self._context.add_user(all_feedback)

            # Context compression: if context exceeds trigger ratio, ask agent to summarize
            compression_trigger = getattr(self, '_compression_trigger', 0.5)
            if self._context.needs_compression(trigger_ratio=compression_trigger):
                target_ratio = getattr(self, '_compression_target', 0.1)
                print(self._stage(_("context_compression", "Context compression"), "active"))
                compress_prompt = self._context.build_compression_prompt(
                    target_ratio=target_ratio)
                self._context.add_user(compress_prompt)

                compress_result = self._provider.send(
                    self._context.get_messages_for_api(),
                    temperature=0.3,
                    max_tokens=4096,
                )
                if compress_result.get("ok") and compress_result.get("text"):
                    self._context.apply_compression(compress_result["text"])
                    print(self._stage(_("context_compressed", "Context compressed."), "done"))
                    _dev_log("context_compressed", {
                        "step": self._iteration,
                        "summary_len": len(compress_result["text"]),
                    })
                else:
                    print(self._detail(
                        f"{YELLOW}{_('compression_failed', 'Compression failed, continuing with full context.')}{RESET}", styled=True))

            time.sleep(0.3)

        if self._iteration >= MAX_ITERATIONS:
            print(self._detail(
                f"{YELLOW}{_('max_iterations', 'Reached maximum iterations ({n}).', n=MAX_ITERATIONS)}{RESET}", styled=True))
            return False
        return True

    def run(self):
        """Main interactive loop."""
        self._init_provider()
        self._print_banner()
        self._write_state("idle")

        try:
            while True:
                if self._pending_cmds:
                    text = self._pending_cmds.pop(0)
                    display_text = text
                    sys.stdout.write(f"\n{self._IDLE} {CYAN}{text}{RESET}\n")
                    sys.stdout.flush()
                else:
                    ctrl = self._read_ctrl()
                    if ctrl:
                        text = ctrl.strip()
                        display_text = text
                    else:
                        user_input = self._prompt()
                        display_text = user_input
                        text = user_input.strip()

                if not text:
                    continue

                cmd_parts = [p.strip() for p in text.split(";") if p.strip()]
                if not cmd_parts:
                    continue
                self._pending_cmds.extend(cmd_parts[1:])
                text = cmd_parts[0]

                if text in ("/quit", "/exit"):
                    self._mark_done(display_text)
                    print(f"  {DIM}{_('goodbye', 'Goodbye.')}{RESET}\n")
                    break

                if text.startswith("/"):
                    if text == "/setup":
                        self._mark_running(display_text)
                        sys.stdout.flush()
                        tracker = _OutputTracker(sys.stdout)
                        sys.stdout = tracker
                        try:
                            self._setup_llm()
                        except Exception as _setup_err:
                            _dev_log("setup_error", {"error": str(_setup_err)})
                        sys.stdout = tracker._wrapped
                        if self._provider and self._provider.is_available():
                            self._recolor_indicator(display_text, tracker.lines, GREEN)
                            print(fmt_status(_('setup_completed', 'Setup completed.')))
                        else:
                            self._recolor_indicator(display_text, tracker.lines, DIM)
                    elif text == "/help":
                        self._mark_done(display_text)
                        self._print_help()
                    elif text == "/new":
                        self._mark_done(display_text)
                        self._checkout_session()
                    elif text == "/sessions":
                        self._mark_done(display_text)
                        self._show_sessions()
                    elif text == "/resume" or text.startswith("/resume "):
                        parts = text.split(None, 1)
                        if len(parts) < 2:
                            self._mark_done(display_text)
                            print(f"  {DIM}Usage: /resume <session-id>{RESET}")
                        else:
                            self._mark_done(display_text)
                            self._checkout_session(parts[1].strip())
                    elif text == "/cleanup":
                        self._mark_running(display_text)
                        tracker = _OutputTracker(sys.stdout)
                        sys.stdout = tracker
                        self._cleanup_session()
                        sys.stdout = tracker._wrapped
                        self._recolor_indicator(display_text, tracker.lines, GREEN)
                    elif text == "/checkout" or text.startswith("/checkout "):
                        parts = text.split(None, 1)
                        sid = parts[1].strip() if len(parts) > 1 else ""
                        self._mark_done(display_text)
                        self._checkout_session(sid)
                    elif text == "/delete" or text.startswith("/delete "):
                        parts = text.split(None, 1)
                        self._mark_running(display_text)
                        tracker = _OutputTracker(sys.stdout)
                        sys.stdout = tracker
                        if len(parts) < 2:
                            self._delete_current_session()
                        else:
                            self._delete_session(parts[1].strip())
                        sys.stdout = tracker._wrapped
                        self._recolor_indicator(display_text, tracker.lines, GREEN)
                    elif text == "/rename" or text.startswith("/rename "):
                        parts = text.split(None, 1)
                        if len(parts) < 2:
                            self._mark_done(display_text)
                            print(f"  {DIM}{_('rename_usage', 'Usage: /rename <session-id> <new title>')}{RESET}")
                        else:
                            self._mark_done(display_text)
                            self._rename_session(parts[1])
                    elif text == "/sandbox" or text.startswith("/sandbox "):
                        parts = text.split(None, 2)
                        if len(parts) >= 3:
                            self._mark_done(display_text)
                            self._manage_sandbox(parts[1], parts[2])
                        else:
                            self._mark_running(display_text)
                            tracker = _OutputTracker(sys.stdout)
                            sys.stdout = tracker
                            self._manage_sandbox()
                            sys.stdout = tracker._wrapped
                            self._recolor_indicator(display_text, tracker.lines, GREEN)
                    elif text == "/models":
                        self._mark_running(display_text)
                        tracker = _OutputTracker(sys.stdout)
                        sys.stdout = tracker
                        self._show_models()
                        sys.stdout = tracker._wrapped
                        self._recolor_indicator(display_text, tracker.lines, GREEN)
                    elif text == "/dashboard":
                        self._mark_running(display_text)
                        tracker = _OutputTracker(sys.stdout)
                        sys.stdout = tracker
                        self._launch_dashboard()
                        sys.stdout = tracker._wrapped
                        self._recolor_indicator(display_text, tracker.lines, GREEN)
                    elif text == "/gui":
                        self._mark_running(display_text)
                        tracker = _OutputTracker(sys.stdout)
                        sys.stdout = tracker
                        self._launch_html_gui()
                        sys.stdout = tracker._wrapped
                        self._recolor_indicator(display_text, tracker.lines, GREEN)
                    elif text == "/status":
                        self._mark_done(display_text)
                        self._show_status()
                    elif text == "/context":
                        self._mark_done(display_text)
                        self._show_context_usage()
                    elif text == "/log" or text.startswith("/log "):
                        self._mark_done(display_text)
                        parts = text.split(None, 1)
                        self._show_log(parts[1].strip() if len(parts) > 1 else "")
                    else:
                        self._mark_failed(display_text)
                        from interface.utils import format_suggestion
                        hint = format_suggestion(text.split()[0], _CMD_NAMES,
                                                 prefix="")
                        if hint:
                            print(f"  {RED}{BOLD}{_('unknown_command', 'Unknown command.')}{RESET} {_('did_you_mean_hint', 'Did you mean: {hint}', hint=hint)}")
                        else:
                            print(f"  {RED}{BOLD}{_('unknown_command', 'Unknown command.')}{RESET} {_('type_help_hint', 'Type /help.')}")
                else:
                    if not self._provider or not self._provider.is_available():
                        self._mark_failed(display_text)
                        print(fmt_status(_('provider_not_configured_label', 'Provider not configured.'),
                                          complement=_('provider_not_configured_hint', 'Run /setup to configure.')))
                        continue
                    self._mark_running(display_text)
                    self._write_state("running", text)
                    tracker = _OutputTracker(sys.stdout)
                    sys.stdout = tracker
                    try:
                        success = self._run_pipeline(text)
                    except KeyboardInterrupt:
                        if self._spinner:
                            self._spinner.stop()
                            self._spinner = None
                        success = False
                    finally:
                        sys.stdout = tracker._wrapped
                    color = GREEN if success else RED
                    self._recolor_indicator(display_text, tracker.lines, color)
                    if not success:
                        print(f"{RED}{self._ACTIVE}{RESET} {_('failed', 'Failed.')}")
                    self._write_state("idle")
        except KeyboardInterrupt:
            if self._spinner:
                self._spinner.stop()
                self._spinner = None
            print(f"\n{DIM}{_('interrupted', 'Interrupted.')}{RESET}\n")
        finally:
            self._cleanup_run_files()
