#!/usr/bin/env python3
"""
GCS upload command: upload local files to remote Google Drive.

Upload strategy by file size:
  - Small  (< 1MB):  Base64-encode and write via Colab bash pipeline.
  - Medium (1-10MB):  Copy to Google Drive Desktop sync folder (LOCAL_EQUIVALENT),
                      wait for sync, then mv to destination on remote.
  - Large  (> 10MB):  Open GUI window for manual drag-and-drop upload.
"""
import os
import sys
import time
import json
import shutil
import base64
import shlex
import hashlib
from pathlib import Path
from interface.config import get_color


SMALL_THRESHOLD = 1 * 1024 * 1024   # 1 MB
LARGE_THRESHOLD = 10 * 1024 * 1024  # 10 MB


def execute(tool, args, state_mgr, load_logic, as_python=False, **kwargs):
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RESET = get_color("RESET", "\033[0m")

    local_path = os.path.abspath(args.local_path)
    remote_path = args.remote_path

    if not os.path.exists(local_path):
        print(f"upload: cannot stat '{args.local_path}': No such file or directory", file=sys.stderr)
        return 1

    if os.path.isdir(local_path):
        print(f"upload: '{args.local_path}': Is a directory (compress with tar/zip first)", file=sys.stderr)
        return 1

    file_size = os.path.getsize(local_path)
    if file_size == 0:
        print(f"upload: '{os.path.basename(local_path)}': Empty file", file=sys.stderr)
        return 1

    utils = load_logic("utils")
    filename = os.path.basename(local_path)

    # Resolve remote destination
    remote_dest_dir = _resolve_remote_dest(args, state_mgr, utils)
    if remote_dest_dir is None:
        print("upload: cannot resolve remote destination", file=sys.stderr)
        return 1

    if file_size < SMALL_THRESHOLD:
        return _upload_small(tool, local_path, filename, file_size,
                             remote_dest_dir, state_mgr, load_logic, as_python)
    elif file_size < LARGE_THRESHOLD:
        return _upload_via_drive_desktop(tool, local_path, filename, file_size,
                                         remote_dest_dir, state_mgr, load_logic, utils, as_python)
    else:
        return _upload_large(tool, local_path, filename, file_size,
                             remote_dest_dir, state_mgr, load_logic, utils, as_python)


def _resolve_remote_dest(args, state_mgr, utils):
    """Resolve the remote destination directory mount path."""
    remote_path = args.remote_path
    if remote_path is None:
        sid = state_mgr.get_active_shell_id()
        info = state_mgr.get_shell_info(sid)
        current_logical = info.get("current_path", "~") if info else "~"
        return utils.logical_to_mount_path(current_logical)

    home = os.path.expanduser("~")
    if remote_path.startswith(home + "/") or remote_path == home:
        remote_path = "~" + remote_path[len(home):]
    rp = remote_path.rstrip("/")
    if "." in os.path.basename(rp) and "/" in rp:
        return utils.logical_to_mount_path(os.path.dirname(rp))
    return utils.logical_to_mount_path(rp)


# ---------------------------------------------------------------------------
#  Strategy 1: Small files via base64 + Colab pipeline
# ---------------------------------------------------------------------------

def _upload_small(tool, local_path, filename, file_size,
                  remote_dest_dir, state_mgr, load_logic, as_python):
    """Upload a small file by base64-encoding and writing through the Colab pipeline."""
    from interface.turing import ProgressTuringMachine, TuringStage

    with open(local_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")

    dest_file = shlex.quote(f"{remote_dest_dir}/{filename}")
    parent_dir = shlex.quote(remote_dest_dir)

    remote_cmd = (
        f"mkdir -p {parent_dir} && "
        f"echo '{encoded}' | base64 -d > {dest_file}"
    )

    upload_result = {}

    def do_upload(stage=None):
        remote_mod = load_logic("command/remote")
        code = remote_mod.execute(tool, remote_cmd, state_mgr, load_logic, as_python=as_python)
        upload_result["code"] = code
        if code != 0 and stage:
            stage.error_brief = "Remote write failed."
        return code == 0

    size_str = _human_size(file_size)
    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage("upload", do_upload,
        active_status="Uploading", active_name=f"{filename} ({size_str})",
        fail_status="Failed to upload", fail_name=filename,
        success_status="Uploaded", success_name=f"{filename} ({size_str})",
        success_color="GREEN"))

    return 0 if pm.run(ephemeral=True) else 1


# ---------------------------------------------------------------------------
#  Strategy 2: Medium files via Google Drive Desktop sync + mv
# ---------------------------------------------------------------------------

def _upload_via_drive_desktop(tool, local_path, filename, file_size,
                               remote_dest_dir, state_mgr, load_logic, utils, as_python):
    """Upload via Google Drive Desktop: copy to sync folder, wait for sync, mv to destination."""
    from interface.turing import ProgressTuringMachine
    from interface.turing import TuringStage

    BOLD = get_color("BOLD", "\033[1m")
    RESET = get_color("RESET", "\033[0m")

    config = utils.get_gcs_config(tool.project_root)
    local_equiv = config.get("local_equivalent")
    drive_equiv = config.get("drive_equivalent")
    drive_equiv_folder_id = config.get("drive_equivalent_folder_id")

    if not local_equiv or not drive_equiv or not drive_equiv_folder_id:
        print(f"upload: Google Drive Desktop sync not configured. "
              f"Run {BOLD}GCS config --local-equivalent <path>{RESET} first, "
              f"or use {BOLD}--force-base64{RESET} flag.", file=sys.stderr)
        return 1

    local_equiv_path = Path(local_equiv)
    if not local_equiv_path.exists():
        print(f"upload: local sync folder does not exist: {local_equiv}", file=sys.stderr)
        return 1

    sync_result = {}

    # Generate a collision-free filename
    final_filename = _safe_filename(filename, local_equiv_path, drive_equiv_folder_id, utils, tool.project_root)

    def copy_stage(stage=None):
        """Copy file to LOCAL_EQUIVALENT."""
        target = local_equiv_path / final_filename
        try:
            shutil.copy2(local_path, str(target))
            sync_result["local_target"] = str(target)
            return True
        except Exception as e:
            if stage:
                stage.error_brief = str(e)
            return False

    def wait_sync_stage(stage=None):
        """Wait for Google Drive Desktop to sync the file."""
        timeout = max(30, int(file_size / (100 * 1024)) + 30)
        return _wait_for_sync(utils, tool.project_root, drive_equiv_folder_id,
                              final_filename, timeout, stage)

    def mv_stage(stage=None):
        """Move the synced file from DRIVE_EQUIVALENT to the destination."""
        source = shlex.quote(f"{drive_equiv}/{final_filename}")
        dest = shlex.quote(f"{remote_dest_dir}/{filename}")
        parent = shlex.quote(remote_dest_dir)

        mv_cmd = f"mkdir -p {parent} && mv {source} {dest}"
        remote_mod = load_logic("command/remote")
        code = remote_mod.execute(tool, mv_cmd, state_mgr, load_logic, as_python=as_python)
        if code != 0:
            if stage:
                stage.error_brief = "Remote mv command failed."
            return False
        return True

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage("copy", copy_stage,
        active_status="Copying", active_name=f"{filename} to sync folder",
        fail_status="Failed to copy", fail_name="file",
        success_status="Copied", success_name="file to sync folder"))
    pm.add_stage(TuringStage("sync", wait_sync_stage,
        active_status="Waiting for", active_name="Google Drive sync",
        fail_status="Sync timed out", fail_name="",
        success_status="Synced", success_name="file"))
    pm.add_stage(TuringStage("move", mv_stage,
        active_status="Moving", active_name="file to destination",
        fail_status="Failed to move", fail_name="file",
        success_status="Uploaded", success_name=f"{filename} ({_human_size(file_size)})",
        success_color="GREEN"))

    if pm.run(ephemeral=True):
        _cleanup_local_equiv(sync_result.get("local_target"))
        return 0
    else:
        _cleanup_local_equiv(sync_result.get("local_target"))
        return 1


# ---------------------------------------------------------------------------
#  Strategy 3: Large files via GUI drag-and-drop
# ---------------------------------------------------------------------------

def _upload_large(tool, local_path, filename, file_size,
                  remote_dest_dir, state_mgr, load_logic, utils, as_python):
    """Show a GUI window instructing the user to manually upload large files."""
    from interface.turing import ProgressTuringMachine
    from interface.turing import TuringStage
    from interface.gui import run_gui_subprocess
    gui_queue_mod = load_logic("command/gui_queue")

    BOLD = get_color("BOLD", "\033[1m")
    RESET = get_color("RESET", "\033[0m")

    config = utils.get_gcs_config(tool.project_root)
    drive_equiv = config.get("drive_equivalent")
    drive_equiv_folder_id = config.get("drive_equivalent_folder_id")

    if not drive_equiv or not drive_equiv_folder_id:
        print(f"upload: Google Drive Desktop not configured for large file upload. "
              f"Run {BOLD}GCS config --drive-equivalent-folder-id <id>{RESET}.", file=sys.stderr)
        return 1

    size_str = _human_size(file_size)
    gui_result = {}

    def gui_stage(stage=None):
        """Show GUI with upload instructions."""
        gui_q = gui_queue_mod.get_gui_queue(tool.project_root)

        script_path = Path(__file__).resolve().parent.parent / "upload_gui.py"
        gui_args = [
            "--file", local_path,
            "--filename", filename,
            "--size", size_str,
            "--project-root", str(tool.project_root),
            "--drive-folder-id", drive_equiv_folder_id
        ]

        old_quiet = getattr(tool, "is_quiet", False)
        tool.is_quiet = True
        try:
            res = gui_q.run_gui_subprocess(
                tool, sys.executable, str(script_path), 600,
                args=gui_args, request_id=f"upload_{int(time.time())}"
            )
        finally:
            tool.is_quiet = old_quiet

        gui_result.update(res)
        if res.get("status") == "success":
            return True
        if stage:
            status = res.get("status", "error")
            if status in ("cancelled", "terminated"):
                stage.fail_status = "Cancelled"
                stage.fail_name = ""
                stage.fail_color = "YELLOW"
                stage.error_brief = "Upload cancelled."
            else:
                stage.error_brief = res.get("message", "Upload GUI closed unexpectedly.")
        return False

    def mv_stage(stage=None):
        """Move the uploaded file from DRIVE_EQUIVALENT to the destination."""
        source = shlex.quote(f"{drive_equiv}/{filename}")
        dest = shlex.quote(f"{remote_dest_dir}/{filename}")
        parent = shlex.quote(remote_dest_dir)

        mv_cmd = (
            f"mkdir -p {parent} && "
            f"for attempt in $(seq 1 30); do "
            f"  if mv {source} {dest} 2>/dev/null; then break; "
            f"  elif [ \"$attempt\" -eq 30 ]; then echo 'mv failed after 30 retries' >&2; exit 1; "
            f"  else sleep 1; fi; "
            f"done"
        )
        remote_mod = load_logic("command/remote")
        code = remote_mod.execute(tool, mv_cmd, state_mgr, load_logic, as_python=as_python)
        if code != 0 and stage:
            stage.error_brief = "Remote mv command failed."
        return code == 0

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage("upload", gui_stage,
        active_status="Waiting for", active_name="manual upload",
        fail_status="Failed to upload", fail_name="file",
        success_status="Uploaded", success_name="file to sync folder"))
    pm.add_stage(TuringStage("move", mv_stage,
        active_status="Moving", active_name="file to destination",
        fail_status="Failed to move", fail_name="file",
        success_status="Uploaded", success_name=f"{filename} ({size_str})",
        success_color="GREEN"))

    return 0 if pm.run(ephemeral=True) else 1


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _safe_filename(filename, local_equiv_path, folder_id, utils, project_root):
    """Generate a collision-free filename for the sync folder."""
    name, ext = os.path.splitext(filename)
    candidate = filename

    for counter in range(1, 101):
        local_exists = (local_equiv_path / candidate).exists()
        if not local_exists:
            remote_exists = _check_remote_exists(utils, project_root, folder_id, candidate)
            if not remote_exists:
                return candidate
        candidate = f"{name}_{counter}{ext}"

    ts = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
    return f"{name}_{ts}{ext}"


def _check_remote_exists(utils, project_root, folder_id, filename):
    """Check if a file with the given name exists in the remote folder."""
    script = f'''    q = "'{folder_id}' in parents and name = {repr(filename)} and trashed = false"
    r = api_get("https://www.googleapis.com/drive/v3/files",
                headers=headers, params={{"q": q, "fields": "files(id)", "pageSize": 1}})
    if r.status_code == 200:
        result = {{"exists": len(r.json().get("files", [])) > 0}}
    else:
        result = {{"exists": False}}'''
    ok, data = utils.run_drive_api_script(project_root, script, timeout=15)
    return ok and data.get("exists", False)


def _wait_for_sync(utils, project_root, folder_id, filename, timeout, stage=None):
    """Poll Drive API until the file appears in the sync folder."""
    start = time.time()
    while time.time() - start < timeout:
        if _check_remote_exists(utils, project_root, folder_id, filename):
            return True
        elapsed = int(time.time() - start)
        if stage:
            stage.active_name = f"Google Drive sync ({elapsed}s)"
            stage.refresh()
        time.sleep(2)
    return False


def _cleanup_local_equiv(local_target):
    """Remove the temp file from the sync folder after successful mv."""
    if local_target:
        try:
            os.remove(local_target)
        except Exception:
            pass


def _human_size(size_bytes):
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}" if unit != "B" else f"{size_bytes}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"
