"""Global keyboard monitoring utility via pynput.

Provides a thin wrapper around pynput's keyboard.Listener for detecting
a paste-then-execute sequence (Cmd/Ctrl+V followed by Enter) from any
application. Used by GUI windows that need to detect when a user has
pasted a command into an external app and pressed Enter.

macOS: Requires Accessibility permissions for the host process.
Use `request_accessibility_permission()` during setup to prompt the user.
"""
import platform
import time
import os
from pathlib import Path
from typing import Callable, Optional


_CMD_KEYS = ('cmd', 'cmd_l', 'cmd_r')
_CTRL_KEYS = ('ctrl_l', 'ctrl_r')
_CMD_VK_CODES = (55, 54)
_PASTE_TIMEOUT = 5.0

_LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tmp" / "keyboard_log"
_log_file = None


def _init_log():
    """Initialize a session log file in tmp/keyboard_log/."""
    global _log_file
    if _log_file is not None:
        return
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        _log_file = _LOG_DIR / f"kb_{ts}_{os.getpid()}.log"
        with open(_log_file, "w") as f:
            f.write(f"# Keyboard monitor session started at {ts}\n")
            f.write(f"# Platform: {platform.system()} {platform.machine()}\n\n")
        # Cleanup old logs (keep last 20)
        logs = sorted(_LOG_DIR.glob("kb_*.log"), key=os.path.getmtime)
        if len(logs) > 20:
            for old in logs[:len(logs) - 20]:
                try: old.unlink()
                except: pass
    except Exception:
        _log_file = None


def _log(msg: str):
    """Append a timestamped message to the keyboard session log."""
    global _log_file
    if _log_file is None:
        _init_log()
    if _log_file is None:
        return
    try:
        ts = time.strftime("%H:%M:%S")
        ms = f"{time.time() % 1:.3f}"[1:]
        with open(_log_file, "a") as f:
            f.write(f"[{ts}{ms}] {msg}\n")
            f.flush()
    except Exception:
        pass


def get_log_file() -> Optional[Path]:
    """Return the path to the current keyboard monitor log file, or None."""
    return _log_file


def is_available() -> bool:
    """Check if pynput is importable."""
    try:
        from pynput import keyboard  # noqa: F401
        return True
    except ImportError:
        return False


def start_paste_enter_listener(on_trigger: Callable[[], None]) -> Optional[object]:
    """Start a listener that fires `on_trigger` after detecting paste then Enter.

    Phase 1: Detects Cmd+V or Ctrl+V (modifier held + 'v' key).
    Phase 2: Within 5 seconds, detects Enter/Return key.

    Returns the listener object (call .stop() to clean up), or None if unavailable.
    """
    try:
        from pynput import keyboard
    except ImportError:
        return None

    state = {"modifier_held": False, "paste_detected": False, "paste_time": 0, "triggered": False}
    _init_log()
    _log(f"start_paste_enter_listener: started (accessibility={check_accessibility_trusted()})")

    def on_press(key):
        if state["triggered"]:
            return False
        try:
            name = getattr(key, 'name', '')
            char = getattr(key, 'char', '')
            vk = getattr(key, 'vk', None)
            _log(f"PRESS name={name!r} char={char!r} vk={vk}")

            if name in _CMD_KEYS or name in _CTRL_KEYS or (vk is not None and vk in _CMD_VK_CODES):
                state["modifier_held"] = True
                _log("  -> MODIFIER DOWN")
                return

            if state["modifier_held"]:
                if char and char.lower() == 'v':
                    state["paste_detected"] = True
                    state["paste_time"] = time.time()
                    _log("  -> PASTE DETECTED (Cmd/Ctrl+V)")
                    return

            if name in ('enter', 'return') or (vk is not None and vk in (36, 76)):
                if state["paste_detected"] and (time.time() - state["paste_time"]) < _PASTE_TIMEOUT:
                    state["triggered"] = True
                    _log("  -> ENTER AFTER PASTE: TRIGGERED!")
                    on_trigger()
                    return False
                elif state["paste_detected"]:
                    _log(f"  -> ENTER but paste timed out ({time.time() - state['paste_time']:.1f}s > {_PASTE_TIMEOUT}s)")
        except Exception as e:
            _log(f"  -> PRESS ERROR: {e}")

    def on_release(key):
        if state["triggered"]:
            return False
        try:
            name = getattr(key, 'name', '')
            vk = getattr(key, 'vk', None)
            if name in _CMD_KEYS or name in _CTRL_KEYS or (vk is not None and vk in _CMD_VK_CODES):
                state["modifier_held"] = False
                _log(f"RELEASE name={name!r} vk={vk} -> MODIFIER UP")
        except Exception:
            pass

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    _log(f"Listener started (daemon thread). Log file: {_log_file}")
    return listener


def start_modifier_listener(on_modifier: Callable[[], None]) -> Optional[object]:
    """Start a global listener that calls `on_modifier` when Cmd or Ctrl is pressed.

    Simpler alternative to start_paste_enter_listener - triggers on any modifier press.
    Returns the listener object (call .stop() to clean up), or None if unavailable.
    """
    try:
        from pynput import keyboard
    except ImportError:
        return None

    def on_press(key):
        try:
            name = getattr(key, 'name', '')
            if name in _CMD_KEYS or name in _CTRL_KEYS:
                on_modifier()
                return False
            if hasattr(key, 'vk') and key.vk in _CMD_VK_CODES:
                on_modifier()
                return False
        except Exception:
            pass

    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()
    return listener


def stop_listener(listener: Optional[object]):
    """Safely stop a pynput listener."""
    if listener is None:
        return
    try:
        listener.stop()
    except Exception:
        pass


def request_accessibility_permission() -> bool:
    """On macOS, show the system accessibility permission prompt.

    Uses AXIsProcessTrustedWithOptions with the prompt flag to trigger
    the native macOS dialog that asks the user to grant permission.
    Returns True if already trusted, False if the prompt was shown.
    """
    if platform.system() != "Darwin":
        return True
    try:
        import ApplicationServices
        options = {ApplicationServices.kAXTrustedCheckOptionPrompt: True}
        return ApplicationServices.AXIsProcessTrustedWithOptions(options)
    except Exception:
        return True


def check_accessibility_trusted() -> bool:
    """Check if the current process is trusted for accessibility on macOS.

    Uses the macOS `AXIsProcessTrusted` API via pyobjc if available.
    Returns True on non-macOS platforms (no permission needed).
    """
    if platform.system() != "Darwin":
        return True
    try:
        import ApplicationServices
        return ApplicationServices.AXIsProcessTrusted()
    except Exception:
        return True


def _run_interactive_test():
    """Launch a tkinter GUI that shows real-time keyboard capture diagnostics.

    Tests:
      1. Accessibility permission status
      2. pynput availability
      3. Raw key event capture (press/release)
      4. Paste+Enter detection sequence
    Invoked via: python -m logic.accessibility.keyboard.monitor
    """
    import tkinter as tk
    from datetime import datetime

    _init_log()
    _log("Interactive test mode started")

    root = tk.Tk()
    root.title("Keyboard Monitor Test")
    root.geometry("620x520")
    root.resizable(True, True)

    # --- Status header ---
    header = tk.Frame(root, padx=10, pady=8)
    header.pack(fill=tk.X)

    pynput_ok = is_available()
    access_ok = check_accessibility_trusted()

    tk.Label(header, text="pynput:", font=("Menlo", 12, "bold")).grid(row=0, column=0, sticky="w")
    tk.Label(header, text="available" if pynput_ok else "NOT FOUND",
             font=("Menlo", 12), fg="green" if pynput_ok else "red").grid(row=0, column=1, sticky="w", padx=(6, 20))
    tk.Label(header, text="Accessibility:", font=("Menlo", 12, "bold")).grid(row=0, column=2, sticky="w")
    access_lbl = tk.Label(header, text="trusted" if access_ok else "NOT trusted",
                          font=("Menlo", 12), fg="green" if access_ok else "red")
    access_lbl.grid(row=0, column=3, sticky="w", padx=(6, 0))

    def refresh_access():
        ok = check_accessibility_trusted()
        access_lbl.config(text="trusted" if ok else "NOT trusted", fg="green" if ok else "red")

    tk.Button(header, text="Refresh", command=refresh_access, font=("Menlo", 10)).grid(row=0, column=4, padx=(10, 0))
    if platform.system() == "Darwin":
        tk.Button(header, text="Request Permission", command=request_accessibility_permission,
                  font=("Menlo", 10)).grid(row=0, column=5, padx=(6, 0))

    # --- Paste+Enter status ---
    pe_frame = tk.Frame(root, padx=10, pady=4)
    pe_frame.pack(fill=tk.X)
    pe_status = tk.StringVar(value="Paste+Enter: waiting...")
    tk.Label(pe_frame, textvariable=pe_status, font=("Menlo", 13, "bold"), fg="gray").pack(anchor="w")

    # --- Event log ---
    log_frame = tk.Frame(root, padx=10, pady=4)
    log_frame.pack(fill=tk.BOTH, expand=True)
    tk.Label(log_frame, text="Key Events (raw pynput output):", font=("Menlo", 11, "bold")).pack(anchor="w")

    log_text = tk.Text(log_frame, font=("Menlo", 11), height=18, wrap=tk.WORD, state=tk.DISABLED)
    scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
    log_text.config(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.pack(fill=tk.BOTH, expand=True)

    event_count = [0]

    def append_log(msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        event_count[0] += 1
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, f"[{ts}] #{event_count[0]:03d}  {msg}\n")
        log_text.see(tk.END)
        log_text.config(state=tk.DISABLED)
        _log(f"GUI #{event_count[0]:03d} {msg}")

    # --- Bottom buttons ---
    btn_frame = tk.Frame(root, padx=10, pady=8)
    btn_frame.pack(fill=tk.X)

    def clear_log():
        event_count[0] = 0
        log_text.config(state=tk.NORMAL)
        log_text.delete("1.0", tk.END)
        log_text.config(state=tk.DISABLED)

    tk.Button(btn_frame, text="Clear Log", command=clear_log, font=("Menlo", 11)).pack(side=tk.LEFT, padx=(0, 10))

    conclusion_var = tk.StringVar(value="")
    tk.Label(btn_frame, textvariable=conclusion_var, font=("Menlo", 11, "bold")).pack(side=tk.RIGHT)

    # --- Start pynput listener ---
    listener_ref = [None]

    if pynput_ok:
        try:
            from pynput import keyboard

            paste_state = {"modifier": False, "pasted": False, "paste_time": 0}

            def on_press(key):
                try:
                    name = getattr(key, 'name', None)
                    char = getattr(key, 'char', None)
                    vk = getattr(key, 'vk', None)
                    desc = f"PRESS   name={name!r}  char={char!r}  vk={vk}"

                    if name in _CMD_KEYS or name in _CTRL_KEYS or (vk is not None and vk in _CMD_VK_CODES):
                        paste_state["modifier"] = True
                        desc += "  [MODIFIER DOWN]"

                    if paste_state["modifier"] and char and char.lower() == 'v':
                        paste_state["pasted"] = True
                        paste_state["paste_time"] = time.time()
                        desc += "  [PASTE DETECTED]"

                    if name in ('enter', 'return') or (vk is not None and vk in (36, 76)):
                        if paste_state["pasted"] and (time.time() - paste_state["paste_time"]) < _PASTE_TIMEOUT:
                            desc += "  [ENTER AFTER PASTE -> TRIGGERED]"
                            root.after(0, lambda: pe_status.set("Paste+Enter: TRIGGERED!"))
                            root.after(0, lambda: conclusion_var.set("Keyboard capture is WORKING."))
                            root.after(1500, root.destroy)

                    root.after(0, lambda d=desc: append_log(d))
                except Exception as exc:
                    root.after(0, lambda: append_log(f"PRESS ERROR: {exc}"))

            def on_release(key):
                try:
                    name = getattr(key, 'name', None)
                    char = getattr(key, 'char', None)
                    vk = getattr(key, 'vk', None)
                    desc = f"RELEASE name={name!r}  char={char!r}  vk={vk}"

                    if name in _CMD_KEYS or name in _CTRL_KEYS or (vk is not None and vk in _CMD_VK_CODES):
                        paste_state["modifier"] = False
                        desc += "  [MODIFIER UP]"

                    root.after(0, lambda d=desc: append_log(d))
                except Exception as exc:
                    root.after(0, lambda: append_log(f"RELEASE ERROR: {exc}"))

            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            listener.daemon = True
            listener.start()
            listener_ref[0] = listener
            append_log("pynput listener started. Press keys anywhere to see events.")
        except Exception as e:
            append_log(f"Failed to start pynput listener: {e}")
    else:
        append_log("pynput is not installed. Install with: pip install pynput")

    # --- Tkinter native key binding (works when window has focus) ---
    tk_paste_state = {"modifier": False, "pasted": False, "paste_time": 0}

    def on_tk_key(event):
        desc = f"TK_KEY  keysym={event.keysym!r}  keycode={event.keycode}  state={event.state:#06x}"

        if event.keysym in ('Meta_L', 'Meta_R', 'Control_L', 'Control_R'):
            tk_paste_state["modifier"] = True

        is_cmd = (event.state & 0x0008) or (event.state & 0x0004)
        if is_cmd and event.keysym.lower() == 'v':
            tk_paste_state["pasted"] = True
            tk_paste_state["paste_time"] = time.time()
            desc += "  [TK PASTE]"

        if event.keysym in ('Return', 'KP_Enter'):
            if tk_paste_state["pasted"] and (time.time() - tk_paste_state["paste_time"]) < _PASTE_TIMEOUT:
                desc += "  [TK PASTE+ENTER -> TRIGGERED]"
                root.after(0, lambda: pe_status.set("Paste+Enter: TRIGGERED! (tkinter)"))
                root.after(0, lambda: conclusion_var.set("Keyboard capture is WORKING (window focus)."))
                root.after(1500, root.destroy)
            tk_paste_state["modifier"] = False

        root.after(0, lambda d=desc: append_log(d))

    root.bind("<Key>", on_tk_key)

    def on_close():
        if listener_ref[0]:
            stop_listener(listener_ref[0])
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Show log file path
    if _log_file:
        log_path_frame = tk.Frame(root, padx=10, pady=2)
        log_path_frame.pack(fill=tk.X, before=btn_frame)
        tk.Label(log_path_frame, text=f"Log: {_log_file}", font=("Menlo", 9), fg="gray").pack(anchor="w")

    # Initial diagnostic summary
    append_log(f"Platform: {platform.system()} {platform.machine()}")
    append_log(f"Python: {platform.python_version()}")
    append_log(f"pynput: {'available' if pynput_ok else 'NOT FOUND'}")
    append_log(f"Accessibility: {'trusted' if access_ok else 'NOT trusted'}")
    append_log("---")
    append_log("Instructions:")
    append_log("  Test 1 (global): Switch to another app, Cmd+V then Enter")
    append_log("  Test 2 (local):  Press Cmd+V then Enter in this window")
    append_log("  Global = pynput events; Local = tkinter events")
    append_log("---")

    root.mainloop()
    _log("Interactive test mode ended")


if __name__ == "__main__":
    _run_interactive_test()
