#!/usr/bin/env python3
"""
GCS Large File Upload GUI: shows instructions for manual drag-and-drop upload.
Buttons: Open Local File, Open Remote Folder, Upload Complete, Cancel.
"""
import sys
import os
import argparse
import subprocess
import webbrowser
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--filename", required=True)
    parser.add_argument("--size", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--drive-folder-id", required=True)
    args = parser.parse_args()

    proj_root = Path(args.project_root)
    if str(proj_root) not in sys.path:
        sys.path.insert(0, str(proj_root))

    from interface.gui import ButtonBarWindow

    drive_url = f"https://drive.google.com/drive/folders/{args.drive_folder_id}"

    def open_local():
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", args.file])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", args.file])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(args.file)])

    def open_remote():
        webbrowser.open(drive_url)

    def on_local_click(btn):
        open_local()
        old_text = btn.cget("text")
        btn.config(text="Opened!", state="disabled")
        btn.after(1500, lambda: btn.config(text=old_text, state="normal"))

    def on_remote_click(btn):
        open_remote()
        old_text = btn.cget("text")
        btn.config(text="Opened!", state="disabled")
        btn.after(1500, lambda: btn.config(text=old_text, state="normal"))

    buttons = [
        {
            "text": "Show File",
            "cmd": open_local,
            "on_click": on_local_click,
            "close_on_click": False
        },
        {
            "text": "Remote Folder",
            "cmd": open_remote,
            "on_click": on_remote_click,
            "close_on_click": False
        },
        {
            "text": "Upload Complete",
            "cmd": None,
            "close_on_click": True
        },
        {
            "text": "Cancel",
            "cmd": None,
            "close_on_click": True
        }
    ]

    instruction = (
        f"Upload **{args.filename}** ({args.size}) to Google Drive.\n"
        f"Drag the file into the **Remote Folder**, then click **Upload Complete**."
    )

    win = ButtonBarWindow(
        title="GCS Large File Upload",
        timeout=600,
        internal_dir=str(proj_root / "tool" / "GOOGLE.GCS" / "logic"),
        buttons=buttons,
        instruction=instruction,
        window_size="520x120"
    )
    win.run()

    result = win.result
    if result and result.get("button") == "Upload Complete":
        result["status"] = "success"
    elif result and result.get("button") == "Cancel":
        result["status"] = "cancelled"

    return result


if __name__ == "__main__":
    main()
