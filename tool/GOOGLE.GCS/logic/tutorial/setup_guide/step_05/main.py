import sys
import tkinter as tk
import threading
from pathlib import Path
from logic.gui.tkinter.style import get_label_style, get_gui_colors, get_button_style

def build_step(frame, win):
    # Title Block
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, "Step 5: Configure Remote Folders", is_title=True)
    
    # Content Block
    content_block = win.add_block(frame)
    content = (
        "1. Enter the Google Drive Folder IDs for your Root and Env folders.\n\n"
        "2. The 'Root Folder' will store your remote file tree structure.\n\n"
        "3. The 'Env Folder' will store your remote environment settings.\n\n"
        "4. Click 'Validate' to ensure the service account has access to both."
    )
    win.setup_label(content_block, content)

    # Action Block
    action_block = win.add_block(frame)
    
    # Grid for inputs
    input_frame = tk.Frame(action_block, bg=action_block.cget("bg"))
    input_frame.pack(pady=10)

    tk.Label(input_frame, text="Root Folder ID:", font=get_label_style(), bg=action_block.cget("bg")).grid(row=0, column=0, sticky="e", padx=5, pady=5)
    root_id_var = tk.StringVar()
    root_entry = tk.Entry(input_frame, textvariable=root_id_var, width=40, font=get_label_style())
    root_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(input_frame, text="Env Folder ID:", font=get_label_style(), bg=action_block.cget("bg")).grid(row=1, column=0, sticky="e", padx=5, pady=5)
    env_id_var = tk.StringVar()
    env_entry = tk.Entry(input_frame, textvariable=env_id_var, width=40, font=get_label_style())
    env_entry.grid(row=1, column=1, padx=5, pady=5)

    status_var = tk.StringVar(value="Enter IDs and click Validate")
    status_label = tk.Label(action_block, textvariable=status_var, font=get_label_style(), fg="gray", bg=action_block.cget("bg"))
    status_label.pack(pady=5)

    btn_frame = tk.Frame(action_block, bg=action_block.cget("bg"))
    btn_frame.pack(pady=10)

    validate_btn = tk.Button(btn_frame, text="Validate Access", bg="white", activebackground="#eee")
    validate_btn.pack()

    def on_validate():
        root_id = root_id_var.get().strip()
        env_id = env_id_var.get().strip()
        
        if not root_id or not env_id:
            status_var.set("Please enter both Folder IDs.")
            status_label.config(fg="red")
            return
            
        validate_btn.config(state=tk.DISABLED, text="Validating...")
        status_var.set("Testing access to Drive folders...")
        status_label.config(fg="gray")
        frame.update_idletasks()

        def run_val():
            try:
                # Import auth module
                import importlib.util
                auth_path = Path(__file__).resolve().parent.parent.parent.parent / "auth.py"
                spec = importlib.util.spec_from_file_location("gcs_auth_step5", str(auth_path))
                auth_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(auth_module)
                
                project_root = getattr(win, "project_root", None) or Path("/Applications/AITerminalTools")
                
                # Validate Root Folder
                ok_root, res_root = auth_module.validate_folder_access(project_root, root_id)
                if not ok_root:
                    def err_root():
                        status_var.set(f"Root Folder Error: {res_root}")
                        status_label.config(fg="red")
                        validate_btn.config(state=tk.NORMAL, text="Validate Access")
                    win.callback_queue.put(err_root)
                    return

                # Validate Env Folder
                ok_env, res_env = auth_module.validate_folder_access(project_root, env_id)
                if not ok_env:
                    def err_env():
                        status_var.set(f"Env Folder Error: {res_env}")
                        status_label.config(fg="red")
                        validate_btn.config(state=tk.NORMAL, text="Validate Access")
                    win.callback_queue.put(err_env)
                    return

                def final_update():
                    auth_module.save_gcs_config(project_root, root_id, env_id)
                    status_var.set(f"Validated! Root: '{res_root}', Env: '{res_env}'")
                    status_label.config(fg="green")
                    win.set_step_validated(True)
                    validate_btn.config(state=tk.NORMAL, text="Validate Access")
                
                win.callback_queue.put(final_update)
            except Exception as e:
                def on_err():
                    status_var.set(f"Validation Logic Error: {e}")
                    status_label.config(fg="red")
                    validate_btn.config(state=tk.NORMAL, text="Validate Access")
                win.callback_queue.put(on_err)

    validate_btn.config(command=on_validate)
    
    # Mark as initially not validated
    win.set_step_validated(False)
