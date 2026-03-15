"""Session export/import — portable knowledge transfer.

Export: Pack session state + memory into a .tar.gz that another agent can import.
Import: Load exported state to give a context-free agent instant knowledge.
"""
import json
import os
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from logic.agent.state import AgentSession, load_session, save_session, get_sessions_dir
from logic.agent.brain import get_experience_dir


def export_session(session_id: str, project_root: str,
                   include_memory: bool = True,
                   output_path: Optional[str] = None) -> str:
    """Export a session + its brain's memory to a .tar.gz archive.

    Returns the path to the created archive.
    """
    session = load_session(session_id, project_root)
    if not session:
        raise FileNotFoundError(f"Session {session_id} not found.")

    if not output_path:
        output_path = os.path.join(
            project_root, "data", "agent_exports",
            f"{session_id}.tar.gz")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with tarfile.open(output_path, "w:gz") as tar:
        session_json = json.dumps(session.to_dict(), indent=2).encode("utf-8")
        info = tarfile.TarInfo(name="session.json")
        info.size = len(session_json)
        tar.addfile(info, BytesIO(session_json))

        if include_memory:
            brain_type = getattr(session, "brain_type", "default") or "default"
            exp_dir = get_experience_dir(project_root, brain_type)
            if exp_dir.exists():
                for fpath in exp_dir.rglob("*"):
                    if fpath.is_file():
                        arcname = f"experience/{fpath.relative_to(exp_dir)}"
                        tar.add(str(fpath), arcname=arcname)

    return output_path


def import_session(archive_path: str, project_root: str,
                   brain_type: str = "default") -> Optional[str]:
    """Import a session + memory from a .tar.gz archive.

    Returns the imported session ID, or None on failure.
    """
    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with tarfile.open(archive_path, "r:gz") as tar:
        session_member = None
        for member in tar.getmembers():
            if member.name == "session.json":
                session_member = member
                break

        if not session_member:
            raise ValueError("Archive does not contain session.json")

        f = tar.extractfile(session_member)
        if not f:
            raise ValueError("Cannot read session.json from archive")
        session_data = json.loads(f.read().decode("utf-8"))
        f.close()

        session = AgentSession(**{k: v for k, v in session_data.items()
                                   if k in AgentSession.__dataclass_fields__})
        save_session(session, project_root)

        exp_dir = get_experience_dir(project_root, brain_type)
        for member in tar.getmembers():
            if member.name.startswith("experience/") and member.isfile():
                rel_path = member.name[len("experience/"):]
                dest = exp_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                src = tar.extractfile(member)
                if src:
                    dest.write_bytes(src.read())
                    src.close()

    return session.id


def list_exports(project_root: str):
    """List available session exports."""
    export_dir = Path(project_root) / "data" / "agent_exports"
    if not export_dir.exists():
        return []
    return sorted(
        ({"name": f.stem, "path": str(f), "size": f.stat().st_size}
         for f in export_dir.glob("*.tar.gz")),
        key=lambda x: x["name"], reverse=True)
