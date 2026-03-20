"""Brain session management.

Each brain session is an isolated namespace containing working memory,
knowledge, episodic data, and a hierarchical manifest. Sessions can be
exported (zip), loaded (unzip), and switched.

Filesystem layout:
    data/_/runtime/_/eco/brain/.active               # Current session name (text file)
    data/_/runtime/_/eco/brain/sessions/
        default/
            MANIFEST.md                 # Hierarchical summary of this brain's contents
            working/
                context.md
                tasks.json
                tasks.md
                activity.jsonl
            knowledge/
                lessons.jsonl
            episodic/
                SOUL.md
                MEMORY.md
                daily/
        senior-dev/
            MANIFEST.md
            ...

Migration from flat layout:
    On first use, if data/_/runtime/_/eco/brain/sessions/ doesn't exist, the current flat
    files (context.md, tasks.json, activity.jsonl) are migrated into
    sessions/default/working/. Experience files are linked from knowledge/.
"""
import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional


SESSIONS_DIR = "sessions"
ACTIVE_FILE = ".active"
DEFAULT_SESSION = "default"


class BrainSessionManager:
    """Manages brain sessions: create, switch, export, load, list."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.brain_root = self.root / "data" / "_" / "runtime" / "_" / "eco" / "brain"
        self.sessions_dir = self.brain_root / SESSIONS_DIR
        self.active_file = self.brain_root / ACTIVE_FILE

    def _ensure_dirs(self):
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def active_session(self) -> str:
        """Get the name of the currently active session."""
        if self.active_file.exists():
            name = self.active_file.read_text(encoding="utf-8").strip()
            if name:
                return name
        return DEFAULT_SESSION

    def session_path(self, name: Optional[str] = None) -> Path:
        """Get the filesystem path for a session."""
        name = name or self.active_session()
        return self.sessions_dir / name

    def list_sessions(self) -> List[Dict]:
        """List all available brain sessions with metadata."""
        self._ensure_dirs()
        sessions = []
        active = self.active_session()
        for d in sorted(self.sessions_dir.iterdir()):
            if not d.is_dir():
                continue
            info = {
                "name": d.name,
                "active": d.name == active,
                "path": str(d),
            }
            manifest = d / "MANIFEST.md"
            if manifest.exists():
                lines = manifest.read_text(encoding="utf-8").split("\n")
                for line in lines:
                    if line.startswith("**Created:**"):
                        info["created"] = line.split("**Created:**")[1].strip()
                    elif line.startswith("**Last updated:**"):
                        info["updated"] = line.split("**Last updated:**")[1].strip()
            working = d / "working"
            if working.exists():
                task_file = working / "tasks.json"
                if task_file.exists():
                    try:
                        tasks = json.loads(task_file.read_text(encoding="utf-8"))
                        info["tasks"] = len(tasks)
                    except Exception:
                        pass
                activity = working / "activity.jsonl"
                if activity.exists():
                    lines = activity.read_text(encoding="utf-8").strip().split("\n")
                    info["activity_entries"] = len([l for l in lines if l.strip()])
            sessions.append(info)
        return sessions

    def list_types(self) -> List[Dict]:
        """List all available brain blueprints from logic/_/brain/blueprint/."""
        from logic._.brain.loader import list_blueprints
        return list_blueprints()

    def create_session(self, name: str, brain_type: Optional[str] = None, soul: Optional[str] = None) -> Path:
        """Create a new brain session with default structure.

        Args:
            name: Session name.
            brain_type: Optional brain type to use (e.g., 'clitools-20260316').
                       If provided, copies blueprint.json and defaults from the type.
            soul: Optional custom SOUL.md content.
        """
        self._ensure_dirs()
        session_dir = self.sessions_dir / name
        if session_dir.exists():
            raise FileExistsError(f"Session '{name}' already exists")

        type_dir = None
        if brain_type:
            from logic._.brain.loader import resolve_blueprint
            type_dir = resolve_blueprint(brain_type)
            if type_dir is None:
                from logic._.brain.loader import list_blueprints
                available = [bp["name"] for bp in list_blueprints()]
                raise FileNotFoundError(
                    f"Blueprint '{brain_type}' not found. Available: {', '.join(available)}"
                )

        (session_dir / "working").mkdir(parents=True)
        (session_dir / "knowledge").mkdir(parents=True)
        (session_dir / "episodic" / "daily").mkdir(parents=True)

        if type_dir:
            bp_src = type_dir / "blueprint.json"
            if bp_src.exists():
                shutil.copy2(bp_src, session_dir / "blueprint.json")

        (session_dir / "working" / "tasks.json").write_text("[]", encoding="utf-8")
        (session_dir / "working" / "context.md").write_text(
            f"# Current Context\n\n**Last updated:** {time.strftime('%Y-%m-%d')}\n"
            f"**Working on:** New session\n**Blocked on:** none\n"
            f"**Brain type:** {brain_type or 'clitools-20260316 (default)'}\n",
            encoding="utf-8",
        )
        (session_dir / "working" / "activity.jsonl").write_text("", encoding="utf-8")

        if soul:
            (session_dir / "episodic" / "SOUL.md").write_text(soul, encoding="utf-8")
        elif type_dir and (type_dir / "defaults" / "SOUL.md").exists():
            shutil.copy2(type_dir / "defaults" / "SOUL.md", session_dir / "episodic" / "SOUL.md")
        else:
            default_soul = self.root / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "default" / "SOUL.md"
            if default_soul.exists():
                shutil.copy2(default_soul, session_dir / "episodic" / "SOUL.md")

        if type_dir and (type_dir / "defaults").exists():
            for default_file in (type_dir / "defaults").rglob("*"):
                if default_file.is_file() and default_file.name != "SOUL.md":
                    rel = default_file.relative_to(type_dir / "defaults")
                    dst = session_dir / "episodic" / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(default_file, dst)

        (session_dir / "episodic" / "MEMORY.md").write_text(
            "# Memory\n\nPersistent facts accumulated during sessions.\n", encoding="utf-8"
        )
        (session_dir / "knowledge" / "lessons.jsonl").write_text("", encoding="utf-8")

        self._generate_manifest(name)
        return session_dir

    def switch_session(self, name: str) -> bool:
        """Switch the active brain session.

        Returns True if switched successfully.
        """
        session_dir = self.sessions_dir / name
        if not session_dir.exists():
            raise FileNotFoundError(f"Session '{name}' not found")
        self.active_file.write_text(name, encoding="utf-8")
        return True

    def export_session(self, name: str, output_path: Optional[Path] = None) -> Path:
        """Export a brain session as a zip file.

        Args:
            name: Session name to export.
            output_path: Output zip path. Defaults to data/_/runtime/_/eco/brain/exports/<name>_<timestamp>.zip

        Returns:
            Path to the created zip file.
        """
        session_dir = self.sessions_dir / name
        if not session_dir.exists():
            raise FileNotFoundError(f"Session '{name}' not found")

        self._generate_manifest(name)

        if output_path is None:
            exports_dir = self.brain_root / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = exports_dir / f"{name}_{timestamp}.zip"

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(session_dir.rglob("*")):
                if file_path.is_file():
                    arcname = file_path.relative_to(session_dir)
                    zf.write(file_path, arcname)

        return output_path

    def load_session(self, zip_path: Path, name: Optional[str] = None) -> str:
        """Load a brain session from a zip file.

        Args:
            zip_path: Path to the zip file.
            name: Optional session name override. If None, uses the zip filename.

        Returns:
            Name of the loaded session.
        """
        self._ensure_dirs()
        if name is None:
            name = Path(zip_path).stem.split("_")[0]

        session_dir = self.sessions_dir / name
        if session_dir.exists():
            raise FileExistsError(f"Session '{name}' already exists. Delete it first or use a different name.")

        session_dir.mkdir(parents=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(session_dir)

        return name

    def migrate_flat_to_session(self) -> bool:
        """Migrate current flat brain files into sessions/default/working/.

        Idempotent: if sessions/default/ already exists, does nothing.
        """
        default_dir = self.sessions_dir / DEFAULT_SESSION
        if default_dir.exists():
            return False

        self._ensure_dirs()
        working_dir = default_dir / "working"
        working_dir.mkdir(parents=True)
        (default_dir / "knowledge").mkdir(parents=True)
        (default_dir / "episodic" / "daily").mkdir(parents=True)

        flat_files = {
            "context.md": working_dir / "context.md",
            "tasks.json": working_dir / "tasks.json",
            "tasks.md": working_dir / "tasks.md",
            "activity.jsonl": working_dir / "activity.jsonl",
        }
        migrated = []
        for src_name, dst_path in flat_files.items():
            src = self.brain_root / src_name
            if src.exists():
                shutil.copy2(src, dst_path)
                migrated.append(src_name)

        global_lessons = self.root / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl"
        if global_lessons.exists():
            shutil.copy2(global_lessons, default_dir / "knowledge" / "lessons.jsonl")
            migrated.append("lessons.jsonl")

        default_experience = self.root / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "default"
        if default_experience.exists():
            for src_file in default_experience.rglob("*"):
                if src_file.is_file():
                    rel = src_file.relative_to(default_experience)
                    dst = default_dir / "episodic" / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst)

        self.active_file.write_text(DEFAULT_SESSION, encoding="utf-8")
        self._generate_manifest(DEFAULT_SESSION)
        return True

    def _generate_manifest(self, name: str):
        """Generate MANIFEST.md for a brain session.

        The manifest is a hierarchical summary of what's in the brain,
        designed to survive export/import and give any agent a quick overview.
        """
        session_dir = self.sessions_dir / name
        if not session_dir.exists():
            return

        lines = [
            f"# Brain: {name}",
            "",
            f"**Created:** {time.strftime('%Y-%m-%d')}",
            f"**Last updated:** {time.strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Overview",
            "",
        ]

        # Working tier summary
        working = session_dir / "working"
        if working.exists():
            lines.append("### Working Memory")
            lines.append("")
            context_file = working / "context.md"
            if context_file.exists():
                content = context_file.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    if line.startswith("**Working on:**") or line.startswith("**Last updated:**"):
                        lines.append(f"- {line.strip()}")
            task_file = working / "tasks.json"
            if task_file.exists():
                try:
                    tasks = json.loads(task_file.read_text(encoding="utf-8"))
                    active = [t for t in tasks if t.get("status") != "done"]
                    done = [t for t in tasks if t.get("status") == "done"]
                    lines.append(f"- Tasks: {len(active)} active, {len(done)} done")
                except Exception:
                    pass
            activity = working / "activity.jsonl"
            if activity.exists():
                entries = [l for l in activity.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
                lines.append(f"- Activity log: {len(entries)} entries")
            lines.append("")

        # Knowledge tier summary
        knowledge = session_dir / "knowledge"
        if knowledge.exists():
            lines.append("### Knowledge")
            lines.append("")
            lessons_file = knowledge / "lessons.jsonl"
            if lessons_file.exists():
                lesson_lines = [l for l in lessons_file.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
                lines.append(f"- Lessons: {len(lesson_lines)} recorded")
                if lesson_lines:
                    try:
                        recent = json.loads(lesson_lines[-1])
                        lines.append(f"- Most recent: {recent.get('lesson', '')[:80]}")
                    except Exception:
                        pass
            lines.append("")

        # Episodic tier summary
        episodic = session_dir / "episodic"
        if episodic.exists():
            lines.append("### Episodic (Personality & Long-term Memory)")
            lines.append("")
            soul = episodic / "SOUL.md"
            if soul.exists():
                content = soul.read_text(encoding="utf-8")
                personality_line = ""
                for line in content.split("\n"):
                    if line.startswith("- ") and not personality_line:
                        personality_line = line[2:].strip()
                if personality_line:
                    lines.append(f"- Personality: {personality_line[:80]}")
            memory = episodic / "MEMORY.md"
            if memory.exists():
                content = memory.read_text(encoding="utf-8")
                mem_lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
                lines.append(f"- Memory entries: {len(mem_lines)}")
            daily = episodic / "daily"
            if daily.exists():
                daily_files = sorted(daily.glob("*.md"))
                if daily_files:
                    lines.append(f"- Daily logs: {len(daily_files)} (latest: {daily_files[-1].stem})")
            lines.append("")

        # File inventory
        lines.append("## File Inventory")
        lines.append("")
        all_files = sorted(f.relative_to(session_dir) for f in session_dir.rglob("*") if f.is_file() and f.name != "MANIFEST.md")
        for f in all_files:
            size = (session_dir / f).stat().st_size
            size_str = f"{size}B" if size < 1024 else f"{size // 1024}KB"
            lines.append(f"- `{f}` ({size_str})")
        lines.append("")

        manifest_path = session_dir / "MANIFEST.md"
        manifest_path.write_text("\n".join(lines), encoding="utf-8")
