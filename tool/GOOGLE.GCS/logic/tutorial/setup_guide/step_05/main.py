import sys
import tkinter as tk
import threading
from pathlib import Path
from logic.gui.tkinter.style import get_label_style, get_gui_colors, get_button_style

def extract_folder_id(input_str):
    """Extracts Google Drive Folder ID from a URL if necessary."""
    input_str = input_str.strip()
    if "drive.google.com" in input_str and "/folders/" in input_str:
        # Extract everything after /folders/ up to next / or ?
        parts = input_str.split("/folders/")
        if len(parts) > 1:
            folder_id = parts[1].split("?")[0].split("/")[0]
            return folder_id
    return input_str

def build_step(frame, win):
    # Title Block
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, "Step 5: Configure Remote Folders", is_title=True)
    
    # Content Block
    service_email = win.tutorial_data.get("service_email", "your service account email")
    content_block = win.add_block(frame)
    content = (
        "1. Open [Google Drive](https://drive.google.com/).\n\n"
        f"2. Select your 'Root' and 'Env' folders and **SHARE** them with: `{service_email}` (give 'Viewer' or 'Editor' access).\n\n"
        "3. Enter the Folder URLs or IDs below.\n\n"
        "4. Click 'Validate' to ensure access is correctly configured."
    )
    win.setup_label(content_block, content)

    # Action Block
    action_block = win.add_block(frame)
    block_bg = "#f9f9f9" if getattr(win, "debug_blocks", False) else action_block.cget("bg")
    
    # Grid for inputs
    input_frame = tk.Frame(action_block, bg=block_bg)
    input_frame.pack(pady=10)

    tk.Label(input_frame, text="Root Folder URL/ID:", font=get_label_style(), bg=block_bg).grid(row=0, column=0, sticky="e", padx=5, pady=5)
    root_id_var = tk.StringVar()
    root_entry = tk.Entry(input_frame, textvariable=root_id_var, width=40, font=get_label_style())
    root_entry.grid(row=0, column=1, padx=5, pady=5)
    root_name_var = tk.StringVar(value="")
    root_name_label = tk.Label(input_frame, textvariable=root_name_var, font=get_label_style(), fg="green", bg=block_bg)
    root_name_label.grid(row=0, column=2, sticky="w", padx=5, pady=5)

    tk.Label(input_frame, text="Env Folder URL/ID:", font=get_label_style(), bg=block_bg).grid(row=1, column=0, sticky="e", padx=5, pady=5)
    env_id_var = tk.StringVar()
    env_entry = tk.Entry(input_frame, textvariable=env_id_var, width=40, font=get_label_style())
    env_entry.grid(row=1, column=1, padx=5, pady=5)
    env_name_var = tk.StringVar(value="")
    env_name_label = tk.Label(input_frame, textvariable=env_name_var, font=get_label_style(), fg="green", bg=block_bg)
    env_name_label.grid(row=1, column=2, sticky="w", padx=5, pady=5)

    status_var = tk.StringVar(value="Enter URL/IDs and click Validate")
    status_label = tk.Label(action_block, textvariable=status_var, font=get_label_style(), fg="gray", bg=block_bg)
    status_label.pack(pady=5)

    btn_frame = tk.Frame(action_block, bg=block_bg)
    btn_frame.pack(pady=10)

    validate_btn = tk.Button(btn_frame, text="Validate Access", bg="white", activebackground="#eee", highlightbackground=block_bg)
    validate_btn.pack()

    def on_validate():
        from logic.gui.tkinter.blueprint.tutorial.gui import log_tutorial
        root_input = root_id_var.get().strip()
        env_input = env_id_var.get().strip()
        log_tutorial(f"Step 5: Validate clicked. Root: {root_input}, Env: {env_input}")
        
        if not root_input or not env_input:
            status_var.set("Please enter both Folder URLs or IDs.")
            status_label.config(fg="red")
            return
            
        root_id = extract_folder_id(root_input)
        env_id = extract_folder_id(env_input)
        
        # Update entry fields with extracted IDs
        root_id_var.set(root_id)
        env_id_var.set(env_id)
        
        # Lock inputs
        root_entry.config(state=tk.DISABLED)
        env_entry.config(state=tk.DISABLED)
        validate_btn.config(state=tk.DISABLED, text="Validating...")
        status_var.set("Testing access to Drive folders...")
        status_label.config(fg="gray")
        frame.update_idletasks()

        def run_val():
            try:
                # Import auth module
                import importlib.util
                auth_path = Path(__file__).resolve().parent.parent.parent.parent / "logic" / "auth.py"
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
                        root_entry.config(state=tk.NORMAL)
                        env_entry.config(state=tk.NORMAL)
                    win.callback_queue.put(err_root)
                    return

                # Validate Env Folder
                ok_env, res_env = auth_module.validate_folder_access(project_root, env_id)
                if not ok_env:
                    def err_env():
                        status_var.set(f"Env Folder Error: {res_env}")
                        status_label.config(fg="red")
                        validate_btn.config(state=tk.NORMAL, text="Validate Access")
                        root_entry.config(state=tk.NORMAL)
                        env_entry.config(state=tk.NORMAL)
                    win.callback_queue.put(err_env)
                    return

                def final_update():
                    auth_module.save_gcs_config(project_root, root_id, env_id)
                    root_name_var.set(f"({res_root})")
                    env_name_var.set(f"({res_env})")
                    status_var.set(f"Validated! Folders ready.")
                    status_label.config(fg="green")
                    win.set_step_validated(True)
                    validate_btn.config(state=tk.NORMAL, text="Validate Access")
                    root_entry.config(state=tk.NORMAL)
                    env_entry.config(state=tk.NORMAL)
                
                win.callback_queue.put(final_update)
            except Exception as e:
                def on_err():
                    status_var.set(f"Validation Logic Error: {e}")
                    status_label.config(fg="red")
                    validate_btn.config(state=tk.NORMAL, text="Validate Access")
                    root_entry.config(state=tk.NORMAL)
                    env_entry.config(state=tk.NORMAL)
                win.callback_queue.put(on_err)

    validate_btn.config(command=on_validate)
