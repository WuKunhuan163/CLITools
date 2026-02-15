import tkinter as tk
import subprocess
import json
import os
import threading
from pathlib import Path
from logic.gui.tkinter.style import get_label_style
from PIL import Image, ImageTk

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

    # Image support
    img_path = Path(__file__).resolve().parent / "asset" / "image" / "guide_1.png"
    if img_path.exists():
        try:
            img = Image.open(img_path)
            if img.width > 500:
                ratio = 500 / img.width
                img = img.resize((500, int(img.height * ratio)), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(frame, image=photo)
            img_label.image = photo
            img_label.pack(pady=5)
        except Exception as e:
            print(f"Error loading image: {e}")

    status_var = tk.StringVar(value="No file selected")
    status_label = tk.Label(frame, textvariable=status_var, font=get_label_style(), fg="gray")
    status_label.pack(pady=5)

    browse_btn = tk.Button(frame, text="Browse and Validate JSON")
    
    def on_browse():
        browse_btn.config(text="Verifying...", state=tk.DISABLED)
        frame.update_idletasks()
        
        # We'll run this in a thread to keep UI responsive, although FILEDIALOG is blocking
        def run_verification():
            project_root = getattr(win, "project_root", None)
            if not project_root:
                curr = Path(__file__).resolve().parent
                while curr != curr.parent:
                    if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
                        project_root = curr
                        break
                    curr = curr.parent

            fd_path = project_root / "bin" / "FILEDIALOG"
            try:
                res = subprocess.run([str(fd_path)], capture_output=True, text=True)
                selected_path = res.stdout.strip()
                
                def update_ui():
                    if res.returncode != 0 or not selected_path:
                        status_var.set("Cancelled or failed")
                        status_label.config(fg="gray")
                        win.set_step_validated(False)
                    else:
                        from tool.GOOGLE.GCS.logic.auth import validate_service_account_json, save_console_key
                        is_valid, err, info = validate_service_account_json(selected_path)
                        if is_valid:
                            saved_path = save_console_key(project_root, info)
                            status_var.set(f"Validated and saved to: {saved_path.name}")
                            status_label.config(fg="green")
                            win.set_step_validated(True)
                        else:
                            status_var.set(f"Validation Error: {err}")
                            status_label.config(fg="red")
                            win.set_step_validated(False)
                    
                    browse_btn.config(text="Browse and Validate JSON", state=tk.NORMAL)

                frame.after(0, update_ui)
            except Exception as e:
                def update_error():
                    status_var.set(f"Error: {e}")
                    status_label.config(fg="red")
                    browse_btn.config(text="Browse and Validate JSON", state=tk.NORMAL)
                frame.after(0, update_error)

        threading.Thread(target=run_verification, daemon=True).start()

    browse_btn.config(command=on_browse)
    browse_btn.pack(pady=10)
    
    # Mark as initially not validated
    win.set_step_validated(False)

