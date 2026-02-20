import sys
import tkinter as tk
import subprocess
import json
import os
import threading
import time
import hashlib
import shutil
from pathlib import Path
from logic.gui.tkinter.style import get_label_style, get_gui_colors

def build_step(frame, win):
    # Title Block
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, "Step 4: Generate JSON Key", is_title=True)
    
    # Content Block
    content_block = win.add_block(frame)
    content = (
        "1. Click on the newly created Service Account from the list.\n\n"
        "2. Go to the 'Keys' tab.\n\n"
        "3. Click 'Add Key' > 'Create New Key'.\n\n"
        "4. Select 'JSON' and click 'Create'.\n\n"
        "5. A JSON file will be downloaded. Click 'Browse' below to select it, then click 'Validate'."
    )
    win.setup_label(content_block, content)

    # Image Block
    img_path = Path(__file__).resolve().parent / "asset" / "image" / "guide_1.png"
    if img_path.exists():
        img_block = win.add_block(frame)
        # max_width=None means use full block width
        win.setup_image(img_block, img_path, upscale=2)

    # Action Block
    action_block = win.add_block(frame)
    # Use a consistent background if debug_blocks is True
    block_bg = "#f9f9f9" if getattr(win, "debug_blocks", False) else action_block.cget("bg")
    
    selected_file_path = tk.StringVar(value="")
    status_var = tk.StringVar(value="No file selected")
    
    status_label = tk.Label(action_block, textvariable=status_var, font=get_label_style(), fg="gray", bg=block_bg)
    status_label.pack(pady=5)

    btn_frame = tk.Frame(action_block, bg=block_bg)
    btn_frame.pack(pady=10)

    browse_btn = tk.Button(btn_frame, text="Browse JSON", bg="white", activebackground="#eee", highlightbackground=block_bg)
    validate_btn = tk.Button(btn_frame, text="Validate", state=tk.DISABLED, bg="white", activebackground="#eee", highlightbackground=block_bg)
    
    browse_btn.pack(side=tk.LEFT, padx=5)
    validate_btn.pack(side=tk.LEFT, padx=5)

    def _get_cache_dir():
        project_root = getattr(win, "project_root", None) or Path("/Applications/AITerminalTools")
        cache_dir = project_root / "data" / "tutorial" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _cleanup_cache(cache_dir, limit=10):
        """Maintains cache limit."""
        files = sorted(list(cache_dir.glob("*.json")), key=os.path.getmtime)
        if len(files) >= limit:
            for i in range(len(files) // 2):
                try: files[i].unlink()
                except: pass

    def on_browse():
        from logic.gui.tkinter.blueprint.tutorial.gui import log_tutorial
        log_tutorial("Step 4: Browse JSON clicked")
        browse_btn.config(state=tk.DISABLED)
        status_var.set("Browsing...")
        status_label.config(fg="gray")
        frame.update_idletasks()
        
        project_root = getattr(win, "project_root", None) or Path("/Applications/AITerminalTools")
        # Use main.py directly to avoid bootstrap overhead and potential shadowing
        fd_main = project_root / "tool" / "FILEDIALOG" / "main.py"
        
        def run_fd():
            try:
                # Absolute log path to ensure it is found
                debug_log = project_root / "tool" / "GOOGLE.GCS" / "data" / "debug_step4.log"
                debug_log.parent.mkdir(parents=True, exist_ok=True)
                def log(msg):
                    with open(debug_log, "a") as f: f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
                    # Also print to stderr for immediate feedback if run in foreground
                    sys.stderr.write(f"DEBUG_LOG: {msg}\n")
                    sys.stderr.flush()
                
                log("run_fd thread started")
                # We use --tool-quiet to minimize noise and get JSON output
                env = os.environ.copy()
                env["PYTHONPATH"] = str(project_root)
                # Ensure we use the main.py correctly
                cmd = [sys.executable, str(fd_main), "--title", "Select Service Account JSON", "--types", "json", "--tool-quiet"]
                log(f"Starting FILEDIALOG via Popen. cmd: {cmd}")
                
                # Use Popen to capture output in real-time
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                
                stdout_lines = []
                stderr_lines = []
                
                def read_out():
                    for line in iter(proc.stdout.readline, ''):
                        stdout_lines.append(line)
                def read_err():
                    for line in iter(proc.stderr.readline, ''):
                        stderr_lines.append(line)
                
                t1 = threading.Thread(target=read_out, daemon=True)
                t2 = threading.Thread(target=read_err, daemon=True)
                t1.start(); t2.start()
                
                # Wait with timeout
                try:
                    ret = proc.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    ret = -1
                
                t1.join(timeout=2); t2.join(timeout=2)
                output = "".join(stdout_lines) + "\n" + "".join(stderr_lines)
                log(f"FILEDIALOG finished. Return code: {ret}")
                
                path = None
                
                # Robust marker search
                marker = "TOOL_RESULT_JSON:"
                for line in output.splitlines():
                    if marker in line:
                        try:
                            json_str = line[line.find(marker) + len(marker):].strip()
                            data = json.loads(json_str)
                            log(f"Found JSON result: {data}")
                            if data.get("returncode") == 0:
                                # Result from FILEDIALOG tool is in its stdout
                                inner_stdout = data.get("stdout", "").strip()
                                if inner_stdout:
                                    path = inner_stdout
                            break
                        except: pass
                
                if not path and ret == 0:
                    log("Marker not found, using direct stdout as fallback")
                    # Fallback to direct stdout if marker not found but process exited successfully
                    path = "".join(stdout_lines).strip()
                
                log(f"Extracted path: {path}")

                def update_ui():
                    log("update_ui callback executing")
                    if path and os.path.exists(path):
                        # Cache the file with hash
                        try:
                            cache_dir = _get_cache_dir()
                            _cleanup_cache(cache_dir)
                            with open(path, 'rb') as f:
                                file_content = f.read()
                            h = hashlib.md5(file_content).hexdigest()[:12]
                            cached_path = cache_dir / f"key_{h}.json"
                            with open(cached_path, 'wb') as f:
                                f.write(file_content)
                            
                            selected_file_path.set(str(cached_path))
                            status_var.set(f"Selected: {os.path.basename(path)}")
                            status_label.config(fg="black")
                            validate_btn.config(state=tk.NORMAL)
                            log(f"UI Updated: validated=True, cache={cached_path}")
                        except Exception as e:
                            log(f"Cache Error: {e}")
                            status_var.set(f"Cache Error: {e}")
                            status_label.config(fg="red")
                    else:
                        log(f"No valid path found (path={path}), resetting UI")
                        status_var.set("No file selected or invalid path")
                        status_label.config(fg="gray")
                        validate_btn.config(state=tk.DISABLED)
                    
                    browse_btn.config(state=tk.NORMAL)
                    log("update_ui callback finished")
                
                # Use callback_queue for thread-safe UI update
                win.callback_queue.put(update_ui)
                log("update_ui scheduled via callback_queue")
            except Exception as e:
                log(f"Exception in run_fd: {e}")
                def on_err():
                    status_var.set(f"Error: {e}")
                    status_label.config(fg="red")
                    browse_btn.config(state=tk.NORMAL)
                win.callback_queue.put(on_err)

        threading.Thread(target=run_fd, daemon=True).start()

    def on_validate():
        from logic.gui.tkinter.blueprint.tutorial.gui import log_tutorial
        path = selected_file_path.get()
        log_tutorial(f"Step 4: Validate clicked. Path: {path}")
        if not path: return
        
        validate_btn.config(state=tk.DISABLED, text="Validating...")
        status_var.set("Validating credentials...")
        frame.update_idletasks()

        def run_val():
            try:
                # Import auth module
                import importlib.util
                auth_path = Path(__file__).resolve().parent.parent.parent.parent / "auth.py"
                spec = importlib.util.spec_from_file_location("gcs_auth_step", str(auth_path))
                auth_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(auth_module)
                
                is_valid, err, info = auth_module.validate_service_account_json(path)
                
                # Check if it matches the email from Step 3
                expected_email = win.tutorial_data.get("service_email")
                if is_valid and expected_email:
                    actual_email = info.get("client_email")
                    if actual_email != expected_email:
                        is_valid = False
                        err = f"Email mismatch! Expected: {expected_email}, Found: {actual_email}"
                
                project_root = getattr(win, "project_root", None) or Path("/Applications/AITerminalTools")
                
                def final_update():
                    if is_valid:
                        saved_path = auth_module.save_console_key(project_root, info)
                        status_var.set(f"Successfully validated and saved!")
                        status_label.config(fg="green")
                        win.set_step_validated(True)
                    else:
                        status_var.set(f"Validation Error: {err}")
                        status_label.config(fg="red")
                        win.set_step_validated(False)
                    
                    validate_btn.config(state=tk.NORMAL, text="Validate")
                
                win.callback_queue.put(final_update)
            except Exception as e:
                def on_err():
                    status_var.set(f"Validation Logic Error: {e}")
                    status_label.config(fg="red")
                    validate_btn.config(state=tk.NORMAL, text="Validate")
                win.callback_queue.put(on_err)

        threading.Thread(target=run_val, daemon=True).start()

    browse_btn.config(command=on_browse)
    validate_btn.config(command=on_validate)
