"""Step 4: Trial execution — test CDP automation with a user command."""
import time
import hashlib
import tkinter as tk
import threading
from pathlib import Path
from interface.gui import get_label_style, get_gui_colors
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

CDP_PORT = 9222


def _run_cdp_execute(command: str, on_log=None, on_done=None):
    """Execute a shell command via CDP and report results.

    Args:
        command: Shell command to execute (without 'GDS' prefix).
        on_log: Callback(str) for log messages (thread-safe via callback_queue).
        on_done: Callback(success, output, error) when done.
    """
    marker = f"GDS_DONE_{hashlib.md5(f'{command}{time.time()}'.encode()).hexdigest()[:8]}"

    if on_log:
        on_log(f"$ GDS {command} --mcp")
        on_log(f"  Marker: {marker}")

    try:
        from tool.GOOGLE.logic.chrome.colab import inject_and_execute
    except ImportError as e:
        if on_done:
            on_done(False, "", str(e))
        return

    cell_code = f"!{command} && echo {marker} || echo {marker}"

    if on_log:
        on_log(f"  Injecting code into Colab cell...")

    result = inject_and_execute(
        code=cell_code, port=CDP_PORT, timeout=60,
        done_marker=marker,
        log_fn=lambda msg: on_log(f"  [CDP] {msg}") if on_log else None
    )

    success = result.get("success", False)
    output = result.get("output", "")
    error = result.get("error", "")

    if on_log:
        if success:
            on_log(f"\n--- Output ---\n{output}\n--- End ---")
        else:
            on_log(f"\n--- Error ---\n{error}\n--- End ---")

    if on_done:
        on_done(success, output, error)


def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block,
        _("mcp_step4_title", "Step 4: Trial Execution"),
        is_title=True)

    content_block = win.add_block(frame)
    win.setup_label(content_block,
        _("mcp_step4_content",
          "Test CDP automation by running a command. "
          "Enter a shell command below and click **Execute**.\n\n"
          "The command will be injected into the Colab notebook "
          "and executed via Chrome DevTools."))

    input_block = win.add_block(frame, pady=(15, 5))
    bg = input_block.cget("bg")
    colors = get_gui_colors()

    input_frame = tk.Frame(input_block, bg=bg)
    input_frame.pack(fill=tk.X, padx=10)

    prefix_label = tk.Label(input_frame, text="GDS ",
                            font=("Menlo", 13, "bold"), bg=bg)
    prefix_label.pack(side=tk.LEFT)

    cmd_entry = tk.Entry(input_frame, font=("Menlo", 13), width=40)
    cmd_entry.insert(0, "echo Hello")
    cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

    execute_btn = tk.Button(input_frame,
        text=_("mcp_step4_execute_btn", "Execute"))
    execute_btn.pack(side=tk.LEFT)

    # Terminal output area
    terminal_frame = tk.Frame(frame, bg="#1e1e1e", bd=1, relief=tk.SUNKEN)
    terminal_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 10))

    terminal_text = tk.Text(terminal_frame,
        bg="#1e1e1e", fg="#d4d4d4", font=("Menlo", 11),
        wrap=tk.WORD, height=10, bd=5,
        insertbackground="#d4d4d4", state=tk.DISABLED)
    scrollbar = tk.Scrollbar(terminal_frame, command=terminal_text.yview)
    terminal_text.config(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    terminal_text.pack(fill=tk.BOTH, expand=True)

    terminal_text.tag_configure("cmd", foreground="#569cd6", font=("Menlo", 11, "bold"))
    terminal_text.tag_configure("info", foreground="#808080")
    terminal_text.tag_configure("output", foreground="#d4d4d4")
    terminal_text.tag_configure("success", foreground="#4ec9b0")
    terminal_text.tag_configure("error", foreground="#f44747")

    status_var = tk.StringVar(value="")
    status_label = tk.Label(frame, textvariable=status_var,
                            font=get_label_style(), fg="gray", bg=frame.cget("bg"))
    status_label.pack(pady=(0, 5))

    callback_queue = []

    def _process_callbacks():
        while callback_queue:
            fn = callback_queue.pop(0)
            try: fn()
            except Exception: pass
        try:
            if frame.winfo_exists():
                frame.after(100, _process_callbacks)
        except tk.TclError:
            pass

    frame.after(100, _process_callbacks)

    def _append_terminal(text, tag="output"):
        def _do():
            terminal_text.config(state=tk.NORMAL)
            terminal_text.insert(tk.END, text + "\n", tag)
            terminal_text.see(tk.END)
            terminal_text.config(state=tk.DISABLED)
        callback_queue.append(_do)

    def _on_execute():
        command = cmd_entry.get().strip()
        if not command:
            return

        execute_btn.config(state="disabled", text=_("mcp_step4_running", "Running..."))
        cmd_entry.config(state="disabled")
        status_var.set(_("mcp_step4_executing", "Executing via CDP..."))

        def _do_clear():
            terminal_text.config(state=tk.NORMAL)
            terminal_text.delete("1.0", tk.END)
            terminal_text.config(state=tk.DISABLED)
        callback_queue.append(_do_clear)

        def _on_log(msg):
            line = msg.strip()
            if line.startswith("$"):
                _append_terminal(line, "cmd")
            elif line.startswith("  [CDP]") or line.startswith("  Marker") or line.startswith("  Inject"):
                _append_terminal(line, "info")
            elif line.startswith("---"):
                _append_terminal(line, "info")
            else:
                _append_terminal(line, "output")

        def _on_done(success, output, error):
            if success:
                def _ok():
                    status_var.set(_("mcp_step4_success", "Execution completed successfully."))
                    status_label.config(fg=colors.get("success", "green"))
                    execute_btn.config(
                        text=_("mcp_step4_execute_btn", "Execute"),
                        state="normal")
                    cmd_entry.config(state="normal")
                    win.set_step_validated(True)
                callback_queue.append(_ok)
            else:
                def _fail():
                    status_var.set(_("mcp_step4_failed",
                        "Execution failed: {error}").format(error=error[:100]))
                    status_label.config(fg=colors.get("error", "red"))
                    execute_btn.config(
                        text=_("mcp_step4_retry", "Retry"),
                        state="normal")
                    cmd_entry.config(state="normal")
                callback_queue.append(_fail)

        threading.Thread(
            target=_run_cdp_execute,
            args=(command,),
            kwargs={"on_log": _on_log, "on_done": _on_done},
            daemon=True
        ).start()

    execute_btn.config(command=_on_execute)
    cmd_entry.bind("<Return>", lambda e: _on_execute())
