"""Workspace management endpoints."""
from __future__ import annotations
from pathlib import Path

_dir = Path(__file__).parent.parent
_root = _dir.parent.parent.parent


class WorkspaceMixin:
    """Workspace management endpoints."""

    def _get_wm(self):
        from interface.workspace import get_workspace_manager
        return get_workspace_manager()

    def _api_workspace_list(self) -> dict:
        wm = self._get_wm()
        return {"ok": True, "workspaces": wm.list_workspaces()}

    def _api_workspace_active(self) -> dict:
        wm = self._get_wm()
        info = wm.active_workspace_info()
        if info:
            info["brain_path"] = str(wm.get_brain_path(info["id"]))
            return {"ok": True, "workspace": info}
        return {"ok": True, "workspace": None}

    def _api_workspace_create(self, body: dict) -> dict:
        path = body.get("path", "").strip()
        name = body.get("name", "").strip() or None
        blueprint = body.get("blueprint", "").strip() or None
        if not path:
            return {"ok": False, "error": "Missing 'path'"}
        wm = self._get_wm()
        try:
            info = wm.create_workspace(path, name=name, blueprint_type=blueprint)
            self._push_sse({"type": "workspace_created", "id": info["id"],
                            "name": info["name"], "path": info["path"]})
            return {"ok": True, "workspace": info}
        except FileExistsError as e:
            return {"ok": False, "error": str(e)}
        except FileNotFoundError as e:
            return {"ok": False, "error": str(e)}

    def _api_workspace_open(self, body: dict) -> dict:
        ws_id = body.get("id", "").strip()
        if not ws_id:
            return {"ok": False, "error": "Missing 'id'"}
        wm = self._get_wm()
        try:
            info = wm.open_workspace(ws_id)
            info["brain_path"] = str(wm.get_brain_path(ws_id))
            self._push_sse({"type": "workspace_opened", "id": ws_id,
                            "name": info["name"], "path": info["path"]})
            return {"ok": True, "workspace": info}
        except FileNotFoundError as e:
            return {"ok": False, "error": str(e)}

    def _api_workspace_close(self) -> dict:
        wm = self._get_wm()
        info = wm.close_workspace()
        if info:
            self._push_sse({"type": "workspace_closed", "id": info["id"]})
            return {"ok": True, "workspace": info}
        return {"ok": False, "error": "No active workspace"}

    def _api_workspace_delete(self, body: dict) -> dict:
        ws_id = body.get("id", "").strip()
        if not ws_id:
            return {"ok": False, "error": "Missing 'id'"}
        wm = self._get_wm()
        try:
            wm.delete_workspace(ws_id)
            self._push_sse({"type": "workspace_deleted", "id": ws_id})
            return {"ok": True}
        except FileNotFoundError as e:
            return {"ok": False, "error": str(e)}

    def _api_workspace_state(self) -> dict:
        """Full workspace state: active workspace, brain info, mounted dir contents."""
        wm = self._get_wm()
        info = wm.active_workspace_info()
        if not info:
            return {"ok": True, "active": False, "workspace": None}

        ws_id = info["id"]
        brain_path = wm.get_brain_path(ws_id)
        mounted_path = info.get("path", "")

        brain_files = {}
        if brain_path.exists():
            for child in sorted(brain_path.rglob("*")):
                if child.is_file():
                    rel = str(child.relative_to(brain_path))
                    try:
                        stat = child.stat()
                        brain_files[rel] = {
                            "size": stat.st_size,
                            "mtime": int(stat.st_mtime),
                        }
                    except OSError:
                        pass

        mounted_listing = []
        try:
            from pathlib import Path
            mp = Path(mounted_path)
            if mp.is_dir():
                for child in sorted(mp.iterdir()):
                    mounted_listing.append({
                        "name": child.name,
                        "type": "dir" if child.is_dir() else "file",
                    })
        except OSError:
            pass

        return {
            "ok": True,
            "active": True,
            "workspace": info,
            "brain_path": str(brain_path),
            "brain_files": brain_files,
            "mounted_path": mounted_path,
            "mounted_listing": mounted_listing[:100],
        }

    def _api_workspace_browse(self, body: dict) -> dict:
        """Launch FILEDIALOG to let the user pick a workspace directory."""
        import subprocess, sys
        try:
            from tool.FILEDIALOG.interface.main import get_file_dialog_bin
            fd_bin = get_file_dialog_bin()
        except ImportError:
            return {"ok": False, "error": "FILEDIALOG not available"}

        initial = body.get("dir", "")
        cmd = [sys.executable, fd_bin, "--directory",
               "--tool-quiet", "--title", "Select Workspace Directory"]
        if initial:
            cmd.extend(["--dir", initial])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=120)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Dialog timed out"}

        if result.returncode != 0:
            return {"ok": False, "error": "Cancelled"}

        import re as _re
        import json as _json
        _ansi_re = _re.compile(r'\x1b\[[0-9;]*m')

        path = ""
        lines = result.stdout.strip().splitlines()

        for line in lines:
            if line.startswith("TOOL_RESULT_JSON:"):
                try:
                    payload = _json.loads(line[len("TOOL_RESULT_JSON:"):])
                    val = payload.get("stdout", "").strip()
                    if val and val != "None":
                        path = val
                except Exception:
                    pass
                break

        if not path:
            for line in lines:
                clean = _ansi_re.sub('', line).strip()
                if clean.startswith("Selected:"):
                    path = clean[len("Selected:"):].strip()
                    if path:
                        break
                m = _re.match(r"^\s*\d+\.\s*(.*)$", clean)
                if m:
                    path = m.group(1).strip()
                    if path:
                        break
        if not path:
            return {"ok": False, "error": "No directory selected"}

        import shlex
        path = path.strip("'\"")
        return {"ok": True, "path": path}

