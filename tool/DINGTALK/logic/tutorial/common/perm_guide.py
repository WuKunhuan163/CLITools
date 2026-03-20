"""Generic permission tutorial factory.

Creates a single-step tutorial that guides users through enabling
specific API permissions in the DingTalk developer console.
"""
import sys
import tkinter as tk
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent


def run_permission_tutorial(
    title: str,
    desc: str,
    permissions: list,
    test_func=None,
    on_step_change=None,
):
    """Run a permission enablement tutorial.

    Args:
        title: Tutorial window title
        desc: Markdown-formatted instructions
        permissions: List of {"scope": str, "name": str, "required": bool} dicts
        test_func: Optional callable() -> {"ok": bool, "error": str} to verify
        on_step_change: Callback(step_idx, total, title)
    """
    project_root = _find_root()
    if project_root:
        root_str = str(project_root)
        if root_str in sys.path:
            sys.path.remove(root_str)
        sys.path.insert(0, root_str)

    from interface.gui import TutorialWindow, TutorialStep, get_label_style
    from tool.DINGTALK.logic.tutorial.common.prereq import check_setup_complete

    def build_prereq_step(frame, win):
        """Check prerequisites before proceeding."""
        block = win.add_block(frame, pady=(20, 10))
        win.setup_label(block, "Checking prerequisites...", is_title=True)

        check = check_setup_complete()
        result_block = win.add_block(frame, pady=(10, 10))

        if check["ok"]:
            label = tk.Label(
                result_block,
                text=f"Setup complete. App: {check['app_key']}\n\nClick Next to continue.",
                font=get_label_style(),
                fg="#228B22",
                bg=result_block.cget("bg"),
                justify="left",
                wraplength=600,
            )
            label.pack(anchor="w", padx=10)
            win.set_step_validated(True)
        else:
            label = tk.Label(
                result_block,
                text=f"Setup required: {check['error']}\n\n"
                     "Please complete the setup tutorial first:\n"
                     "  DINGTALK --tutorial setup",
                font=get_label_style(),
                fg="#cc3333",
                bg=result_block.cget("bg"),
                justify="left",
                wraplength=600,
            )
            label.pack(anchor="w", padx=10)
            win.set_step_validated(False)

    def build_permissions_step(frame, win):
        """Show permission instructions."""
        block = win.add_block(frame, pady=(20, 10))
        win.setup_label(block, title, is_title=True)

        content_block = win.add_block(frame)
        win.add_inline_links(content_block, description)

        perm_block = win.add_block(frame, pady=(10, 5))
        perm_lines = []
        for p in permissions:
            req = " (required)" if p.get("required", True) else " (optional)"
            perm_lines.append(f"  `{p['scope']}` — {p['name']}{req}")
        perm_text = "**Permissions to enable:**\n\n" + "\n".join(perm_lines)
        win.add_inline_links(perm_block, perm_text)

        win.set_step_validated(True)

    def build_verify_step(frame, win):
        """Optionally verify permissions."""
        block = win.add_block(frame, pady=(20, 10))
        win.setup_label(block, "Verify Permissions", is_title=True)

        result_block = win.add_block(frame, pady=(10, 10))

        if test_func:
            result = test_func()
            if result.get("ok"):
                text = "Permissions verified successfully!\n\nYou can now use the related DINGTALK commands."
                color = "#228B22"
            else:
                text = (f"Verification: {result.get('error', 'Unknown')}\n\n"
                        "If you just enabled the permissions, they may take a few minutes to activate.\n"
                        "You can retry later with the DINGTALK command directly.")
                color = "#cc9900"
        else:
            text = ("Permissions should now be enabled.\n\n"
                    "Test by running the related DINGTALK commands.\n"
                    "If you get permission errors, check the developer console.")
            color = "#228B22"

        label = tk.Label(
            result_block, text=text, font=get_label_style(), fg=color,
            bg=result_block.cget("bg"), justify="left", wraplength=600,
        )
        label.pack(anchor="w", padx=10)
        win.set_step_validated(True)

    steps = [
        TutorialStep("Prerequisites", build_prereq_step),
        TutorialStep("Enable Permissions", build_permissions_step),
        TutorialStep("Verify", build_verify_step),
    ]

    win = TutorialWindow(
        title=title,
        timeout=300,
        steps=steps,
        internal_dir=str(Path(__file__).resolve().parent),
        on_step_change=on_step_change,
    )
    win.run(win.setup_ui)
    return win.result


def _find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None
