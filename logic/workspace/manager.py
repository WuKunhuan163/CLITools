"""Workspace manager: create, open, close, delete, list workspaces.

A workspace is a user directory mounted into the system. All workspace
metadata and brain data are stored inside AITerminalTools (not in the
target directory), preventing filesystem collisions.

Filesystem layout:
    workspace/
        <hash_id>/
            workspace.json     # Metadata (path, name, created, blueprint)
            brain/             # Brain instance data (scoped to this workspace)
                working/
                knowledge/
                episodic/
                MANIFEST.md
            README.md          # Auto-generated workspace overview
            for_agent.md       # Agent guidance for this workspace
"""
import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional


def _hash_path(path: str) -> str:
    """Generate a short deterministic hash ID from a directory path."""
    normalized = str(Path(path).resolve())
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


class WorkspaceManager:
    """Manages workspaces: create, open, close, delete, list."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.ws_root = self.root / "workspace"
        self._active_file = self.ws_root / ".active"

    def _ensure_dirs(self):
        self.ws_root.mkdir(parents=True, exist_ok=True)

    def active_workspace(self) -> Optional[str]:
        """Get the currently active workspace ID, or None."""
        if self._active_file.exists():
            ws_id = self._active_file.read_text(encoding="utf-8").strip()
            if ws_id and (self.ws_root / ws_id).exists():
                return ws_id
        return None

    def active_workspace_info(self) -> Optional[Dict]:
        """Get full info for the active workspace."""
        ws_id = self.active_workspace()
        if ws_id:
            return self._load_meta(ws_id)
        return None

    def list_workspaces(self) -> List[Dict]:
        """List all registered workspaces."""
        self._ensure_dirs()
        active = self.active_workspace()
        results = []
        for d in sorted(self.ws_root.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            meta_file = d / "workspace.json"
            if not meta_file.exists():
                continue
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                meta["id"] = d.name
                meta["active"] = d.name == active
                results.append(meta)
            except Exception:
                pass
        return results

    def create_workspace(self, target_path: str,
                         name: Optional[str] = None,
                         blueprint_type: Optional[str] = None) -> Dict:
        """Create a new workspace for a target directory.

        Args:
            target_path: Absolute path to the user's working directory.
            name: Optional human-friendly name (defaults to directory name).
            blueprint_type: Brain blueprint to use (default: clitools-20260316).

        Returns:
            Dict with workspace info including 'id'.
        """
        target = Path(target_path).resolve()
        if not target.is_dir():
            raise FileNotFoundError(f"Directory not found: {target}")

        ws_id = _hash_path(str(target))
        ws_dir = self.ws_root / ws_id

        if ws_dir.exists():
            meta = self._load_meta(ws_id)
            if meta:
                raise FileExistsError(
                    f"Workspace already exists for '{target}' (id: {ws_id})"
                )

        self._ensure_dirs()
        ws_dir.mkdir(parents=True, exist_ok=True)

        bp_type = blueprint_type or "clitools-20260316"
        ws_name = name or target.name

        brain_dir = ws_dir / "brain"
        (brain_dir / "working").mkdir(parents=True)
        (brain_dir / "knowledge").mkdir(parents=True)
        (brain_dir / "episodic" / "daily").mkdir(parents=True)

        if blueprint_type:
            from logic.brain.loader import resolve_blueprint
            bp_dir = resolve_blueprint(blueprint_type)
            if bp_dir and (bp_dir / "blueprint.json").exists():
                shutil.copy2(bp_dir / "blueprint.json", brain_dir / "blueprint.json")
            if bp_dir and (bp_dir / "defaults").exists():
                for f in (bp_dir / "defaults").rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(bp_dir / "defaults")
                        dst = brain_dir / "episodic" / rel
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dst)

        (brain_dir / "working" / "context.md").write_text(
            f"# Current Context\n\n**Last updated:** {time.strftime('%Y-%m-%d')}\n"
            f"**Workspace:** {ws_name}\n**Path:** {target}\n"
            f"**Working on:** New workspace\n**Blocked on:** none\n",
            encoding="utf-8",
        )
        (brain_dir / "working" / "tasks.json").write_text("[]", encoding="utf-8")
        (brain_dir / "working" / "activity.jsonl").write_text("", encoding="utf-8")
        (brain_dir / "knowledge" / "lessons.jsonl").write_text("", encoding="utf-8")
        (brain_dir / "episodic" / "MEMORY.md").write_text(
            "# Memory\n\nPersistent facts for this workspace.\n", encoding="utf-8"
        )

        meta = {
            "id": ws_id,
            "name": ws_name,
            "path": str(target),
            "blueprint_type": bp_type,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "last_opened": None,
            "status": "closed",
        }
        (ws_dir / "workspace.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        self._write_readme(ws_id, meta)
        self._write_for_agent(ws_id, meta)

        return meta

    def open_workspace(self, ws_id: str) -> Dict:
        """Open (activate) a workspace."""
        ws_dir = self.ws_root / ws_id
        if not ws_dir.exists():
            raise FileNotFoundError(f"Workspace not found: {ws_id}")

        meta = self._load_meta(ws_id)
        if not meta:
            raise FileNotFoundError(f"Workspace metadata missing: {ws_id}")

        target = Path(meta["path"])
        if not target.exists():
            raise FileNotFoundError(
                f"Workspace target directory missing: {meta['path']}"
            )

        meta["status"] = "open"
        meta["last_opened"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save_meta(ws_id, meta)
        self._active_file.write_text(ws_id, encoding="utf-8")

        return meta

    def close_workspace(self) -> Optional[Dict]:
        """Close the currently active workspace."""
        ws_id = self.active_workspace()
        if not ws_id:
            return None

        meta = self._load_meta(ws_id)
        if meta:
            meta["status"] = "closed"
            self._save_meta(ws_id, meta)

        if self._active_file.exists():
            self._active_file.unlink()

        return meta

    def delete_workspace(self, ws_id: str) -> bool:
        """Delete a workspace and all its data."""
        ws_dir = self.ws_root / ws_id
        if not ws_dir.exists():
            raise FileNotFoundError(f"Workspace not found: {ws_id}")

        if self.active_workspace() == ws_id:
            self.close_workspace()

        shutil.rmtree(ws_dir)
        return True

    def get_workspace_path(self, ws_id: str) -> Path:
        """Get the internal data path for a workspace."""
        return self.ws_root / ws_id

    def get_brain_path(self, ws_id: Optional[str] = None) -> Path:
        """Get the brain data path for a workspace."""
        ws_id = ws_id or self.active_workspace()
        if not ws_id:
            return self.root / "runtime" / "brain"
        return self.ws_root / ws_id / "brain"

    def _load_meta(self, ws_id: str) -> Optional[Dict]:
        meta_file = self.ws_root / ws_id / "workspace.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                meta["id"] = ws_id
                return meta
            except Exception:
                pass
        return None

    def _save_meta(self, ws_id: str, meta: Dict):
        meta_file = self.ws_root / ws_id / "workspace.json"
        (self.ws_root / ws_id).mkdir(parents=True, exist_ok=True)
        clean = {k: v for k, v in meta.items() if k != "active"}
        meta_file.write_text(
            json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _write_readme(self, ws_id: str, meta: Dict):
        readme = self.ws_root / ws_id / "README.md"
        readme.write_text(
            f"# Workspace: {meta['name']}\n\n"
            f"**ID:** `{ws_id}`\n"
            f"**Target:** `{meta['path']}`\n"
            f"**Blueprint:** `{meta['blueprint_type']}`\n"
            f"**Created:** {meta['created']}\n\n"
            f"## Structure\n\n"
            f"```\nworkspace/{ws_id}/\n"
            f"├── workspace.json    # Metadata\n"
            f"├── brain/            # Brain instance (scoped to this workspace)\n"
            f"│   ├── working/      # Tasks, context, activity\n"
            f"│   ├── knowledge/    # Lessons\n"
            f"│   └── episodic/     # Personality, memory, daily logs\n"
            f"├── README.md         # This file\n"
            f"└── for_agent.md      # Agent guidance\n```\n",
            encoding="utf-8",
        )

    def _write_for_agent(self, ws_id: str, meta: Dict):
        fa = self.ws_root / ws_id / "for_agent.md"
        fa.write_text(
            f"# Workspace Agent Guide: {meta['name']}\n\n"
            f"This workspace targets `{meta['path']}`.\n\n"
            f"## Brain\n\n"
            f"Brain data for this workspace is at `workspace/{ws_id}/brain/`.\n"
            f"Blueprint: `{meta['blueprint_type']}`\n\n"
            f"## TODO\n\n"
            f"- (Record workspace-specific development tasks here)\n\n"
            f"## Notes\n\n"
            f"- (Record workspace-specific findings and context here)\n",
            encoding="utf-8",
        )
