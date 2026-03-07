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
from interface.gui import get_label_style, get_gui_colors
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

def _get_log_path():
    """Returns path to debug log file for step 4 diagnostics."""
    p = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "debug_step4.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _log(msg):
    ts = time.strftime("%H:%M:%S")
    try:
        with open(_get_log_path(), "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _("tutorial_step4_title", "Step 4: Generate JSON Key"), is_title=True)
    
    # Content Block
    content_block = win.add_block(frame)
    content = _(
        "tutorial_step4_content",
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
        win.setup_image(img_block, img_path, upscale=2)

    # Action Block
    action_block = win.add_block(frame)
    selected_file_path = tk.StringVar(value="")
    status_var = tk.StringVar(value=_("tutorial_step4_no_file", "No file selected"))
    
    status_label = tk.Label(action_block, textvariable=status_var, font=get_label_style(), fg="gray", bg=action_block.cget("bg"))
    status_label.pack(pady=5)

    btn_frame = tk.Frame(action_block, bg=action_block.cget("bg"))
    btn_frame.pack(pady=10)

    browse_btn = tk.Button(btn_frame, text=_("tutorial_step4_browse_btn", "Browse JSON"))
    validate_btn = tk.Button(btn_frame, text=_("tutorial_step4_validate_btn", "Validate"), state=tk.DISABLED)
    
    browse_btn.pack(side=tk.LEFT, padx=5)
    validate_btn.pack(side=tk.LEFT, padx=5)

    callback_queue = []

    def _process_callbacks():
        while callback_queue:
            fn = callback_queue.pop(0)
            try:
                fn()
            except Exception:
                pass
        try:
            if frame.winfo_exists():
                frame.after(100, _process_callbacks)
        except tk.TclError:
            pass

    frame.after(100, _process_callbacks)

    def _get_cache_dir():
        project_root = getattr(win, "project_root", None)
        cache_dir = project_root / "data" / "tutorial" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _cleanup_cache(cache_dir, keep_latest_only=True):
        """Remove old cached keys. If keep_latest_only, remove all but the newest."""
        files = sorted(list(cache_dir.glob("key_*.json")), key=os.path.getmtime)
        if keep_latest_only and len(files) > 0:
            for f in files[:-1]:
                try: f.unlink()
                except: pass
        elif len(files) >= 10:
            for f in files[:len(files) // 2]:
                try: f.unlink()
                except: pass

    def on_browse():
        browse_btn.config(state=tk.DISABLED)
        status_var.set(_("tutorial_step4_browsing", "Browsing..."))
        frame.update_idletasks()
        
        project_root = getattr(win, "project_root", None)
        fd_main = project_root / "tool" / "FILEDIALOG" / "main.py"

        def run_fd():
            _log("run_fd thread started")
            py_exe = sys.executable

            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)
            cmd = [str(py_exe), str(fd_main), "--title", _("tutorial_step4_select_json", "Select Service Account JSON"), "--types", "json", "--tool-quiet"]
            _log(f"Starting FILEDIALOG via Popen. cmd: {cmd}")

            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, env=env, bufsize=1
                )
                if hasattr(win, 'register_child_proc'):
                    win.register_child_proc(proc)
                
                output_lines = []
                for line in proc.stdout:
                    stripped = line.rstrip("\n")
                    output_lines.append(stripped)
                    _log(f"  STDOUT: {stripped[:200]}")
                proc.wait()
                
                _log(f"FILEDIALOG finished. Return code: {proc.returncode}. Lines: {len(output_lines)}")

                path = None
                marker = "TOOL_RESULT_JSON:"
                for line in output_lines:
                    if marker in line:
                        try:
                            json_str = line[line.find(marker) + len(marker):].strip()
                            data = json.loads(json_str)
                            _log(f"Found JSON result: {data}")
                            if data.get("returncode") == 0:
                                inner_stdout = data.get("stdout", "").strip()
                                if inner_stdout:
                                    path = inner_stdout
                            break
                        except Exception:
                            pass

                if not path and proc.returncode == 0:
                    combined = "\n".join(output_lines).strip()
                    last_line = combined.splitlines()[-1] if combined else ""
                    if last_line and os.path.exists(last_line):
                        path = last_line

                _log(f"Extracted path: {path}")

                def update_ui():
                    _log("update_ui callback executing")
                    if path and os.path.exists(path):
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
                            basename = os.path.basename(path)
                            status_var.set(_("tutorial_step4_selected", "Selected: {filename}", filename=basename))
                            status_label.config(fg="black")
                            validate_btn.config(state=tk.NORMAL)
                            _log(f"UI Updated: validated=True, cache={cached_path}")
                        except Exception as e:
                            status_var.set(_("tutorial_step4_cache_error", "Cache Error: {error}", error=str(e)))
                            status_label.config(fg="red")
                    else:
                        _log(f"No valid path found (path={path}), resetting UI")
                        status_var.set(_("tutorial_step4_no_file_or_invalid", "No file selected or invalid path"))
                        status_label.config(fg="gray")
                        validate_btn.config(state=tk.DISABLED)
                    
                    browse_btn.config(state=tk.NORMAL)
                    _log("update_ui callback finished")

                _log("update_ui scheduled via callback_queue")
                callback_queue.append(update_ui)

            except Exception as e:
                _log(f"Exception in run_fd: {e}")
                def on_err():
                    status_var.set(_("tutorial_step4_error", "Error: {error}", error=str(e)))
                    status_label.config(fg="red")
                    browse_btn.config(state=tk.NORMAL)
                callback_queue.append(on_err)

        threading.Thread(target=run_fd, daemon=True).start()

    def on_validate():
        path = selected_file_path.get()
        if not path: return
        
        validate_btn.config(state=tk.DISABLED, text=_("tutorial_step4_validating_btn", "Validating..."))
        status_var.set(_("tutorial_step4_validating_creds", "Validating credentials..."))
        frame.update_idletasks()

        def run_val():
            try:
                import importlib.util
                auth_path = Path(__file__).resolve().parent.parent.parent.parent / "auth.py"
                spec = importlib.util.spec_from_file_location("gcs_auth_step", str(auth_path))
                auth_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(auth_module)
                
                is_valid, err, info = auth_module.validate_service_account_json(path)
                project_root = getattr(win, "project_root", None)
                
                def final_update():
                    if is_valid:
                        saved_path = auth_module.save_console_key(project_root, info)
                        status_var.set(_("tutorial_step4_success", "Successfully validated and saved!"))
                        status_label.config(fg="green")
                        win.set_step_validated(True)
                    else:
                        status_var.set(_("tutorial_step4_validation_error", "Validation Error: {error}", error=err))
                        status_label.config(fg="red")
                        win.set_step_validated(False)
                    
                    validate_btn.config(state=tk.NORMAL, text=_("tutorial_step4_validate_btn", "Validate"))
                
                callback_queue.append(final_update)
            except Exception as e:
                def on_err():
                    status_var.set(_("tutorial_step4_logic_error", "Validation Logic Error: {error}", error=str(e)))
                    status_label.config(fg="red")
                    validate_btn.config(state=tk.NORMAL, text=_("tutorial_step4_validate_btn", "Validate"))
                callback_queue.append(on_err)

        threading.Thread(target=run_val, daemon=True).start()

    browse_btn.config(command=on_browse)
    validate_btn.config(command=on_validate)

    _already_validated = [False]

    def _load_cached_key():
        """Load the most recent cached key file on startup."""
        try:
            cache_dir = _get_cache_dir()
            cached_keys = sorted(list(cache_dir.glob("key_*.json")), key=os.path.getmtime, reverse=True)
            if cached_keys:
                latest = cached_keys[0]
                with open(latest, 'r') as f:
                    json.load(f)
                selected_file_path.set(str(latest))
                status_var.set(_("tutorial_step4_loaded_cache", "Loaded cached key: {name}", name=latest.name))
                status_label.config(fg="green")
                validate_btn.config(state=tk.NORMAL)
                project_root = getattr(win, "project_root", None)
                if project_root:
                    saved_key = project_root / "data" / "google_cloud_console" / "service_account_key.json"
                    if saved_key.exists():
                        with open(saved_key, 'rb') as f1, open(latest, 'rb') as f2:
                            if f1.read() == f2.read():
                                status_var.set(_("tutorial_step4_already_validated", "Key already validated and saved."))
                                _already_validated[0] = True
                                return
        except Exception:
            pass

    _load_cached_key()

    if _already_validated[0]:
        win.set_step_validated(True)
    else:
        win.set_step_validated(False)
