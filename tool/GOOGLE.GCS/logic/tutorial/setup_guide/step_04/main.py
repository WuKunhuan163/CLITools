import tkinter as tk
import subprocess
import json
import os
from pathlib import Path
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    tk.Label(frame, text="Step 4: Generate JSON Key", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. Click on the newly created Service Account from the list.\n\n"
        "2. Go to the 'Keys' tab.\n\n"
        "3. Click 'Add Key' > 'Create New Key'.\n\n"
        "4. Select 'JSON' and click 'Create'.\n\n"
        "5. A JSON file will be downloaded. Click 'Browse' below to select and validate it."
    )
    
    tk.Label(frame, text=content, font=get_label_style(), justify="left", wraplength=600).pack(pady=10, padx=20)

    status_var = tk.StringVar(value="No file selected")
    status_label = tk.Label(frame, textvariable=status_var, font=get_label_style(), fg="gray")
    status_label.pack(pady=5)

    def on_browse():
        # Call FILEDIALOG
        project_root = win.project_root # Assuming TutorialWindow has project_root
        if not project_root:
            # Fallback to find root
            curr = Path(__file__).resolve().parent
            while curr != curr.parent:
                if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
                    project_root = curr
                    break
                curr = curr.parent

        fd_path = project_root / "bin" / "FILEDIALOG"
        try:
            # Use safe python for GUI to run FILEDIALOG if needed, or just run it directly
            res = subprocess.run([str(fd_path)], capture_output=True, text=True)
            if res.returncode == 0:
                selected_path = res.stdout.strip()
                if not selected_path:
                    status_var.set("Cancelled")
                    return
                
                # Validate
                from tool.GOOGLE.GCS.logic.auth import validate_service_account_json, save_console_key
                is_valid, err, info = validate_service_account_json(selected_path)
                if is_valid:
                    saved_path = save_console_key(project_root, info)
                    status_var.set(f"Validated and saved to: {saved_path.name}")
                    status_label.config(fg="green")
                    # Enable next button or mark step as complete
                    win.set_step_validated(True)
                else:
                    status_var.set(f"Validation Error: {err}")
                    status_label.config(fg="red")
                    win.set_step_validated(False)
        except Exception as e:
            status_var.set(f"Error: {e}")
            status_label.config(fg="red")

    tk.Button(frame, text="Browse and Validate JSON", command=on_browse).pack(pady=10)
    
    # Mark as initially not validated if it's the current step
    win.set_step_validated(False)

