"""Git persistence manager -- locker for untracked data across branch switches.

Saves untracked directories (e.g. tool/*/data/ containing API keys, caches,
configs) to a system temp location before a branch switch, and restores
them afterward. Lockers are identified by opaque keys and subject to a
count limit and a TTL (time-to-live) expiry.
"""
import os
import shutil
import json
import tempfile
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

_DEFAULT_LIMIT = 8
_DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days


class GitPersistenceManager:
    """Manages persistence of untracked tool directories across branch switches."""

    def __init__(self, project_root: Path, *, limit: int = _DEFAULT_LIMIT,
                 ttl_seconds: int = _DEFAULT_TTL_SECONDS):
        self.project_root = project_root
        self.temp_base = Path(tempfile.gettempdir()) / "aitools_git_persistence"
        self.temp_base.mkdir(parents=True, exist_ok=True)
        self.limit = limit
        self.ttl_seconds = ttl_seconds

    # ------------------------------------------------------------------
    # Cleanup helpers
    # ------------------------------------------------------------------

    def _cleanup_expired(self):
        """Remove lockers older than TTL."""
        now = time.time()
        for d in list(self.temp_base.iterdir()):
            if not d.is_dir():
                continue
            meta = d / ".locker_meta.json"
            if meta.exists():
                try:
                    created = json.loads(meta.read_text()).get("created", 0)
                    if now - created > self.ttl_seconds:
                        shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass
            else:
                age = now - d.stat().st_mtime
                if age > self.ttl_seconds:
                    shutil.rmtree(d, ignore_errors=True)

    def _cleanup_over_limit(self):
        """If lockers exceed the limit, delete the oldest half."""
        caches = sorted(
            [d for d in self.temp_base.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
        )
        if len(caches) >= self.limit:
            to_delete = len(caches) // 2
            for d in caches[:to_delete]:
                shutil.rmtree(d, ignore_errors=True)

    def cleanup(self):
        """Run both expiry and limit cleanup."""
        self._cleanup_expired()
        self._cleanup_over_limit()

    # ------------------------------------------------------------------
    # Key generation
    # ------------------------------------------------------------------

    def _generate_key(self, branch: str = "") -> str:
        ts = time.strftime("%Y%m%d_%H%M%S")
        rand = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        tag = f"_{branch}" if branch else ""
        return f"{ts}{tag}_{rand}"

    # ------------------------------------------------------------------
    # Save / restore
    # ------------------------------------------------------------------

    def save(self, paths: List[Path], *, branch: str = "") -> Optional[str]:
        """Save *paths* into a new locker. Returns the locker key or ``None``."""
        if not paths:
            return None

        self.cleanup()

        key = self._generate_key(branch)
        storage = self.temp_base / key
        storage.mkdir(parents=True, exist_ok=True)

        found_any = False
        for src in paths:
            if not src.exists():
                continue
            try:
                rel = src.relative_to(self.project_root)
                dest = storage / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dest)
                found_any = True
            except ValueError:
                continue

        if found_any:
            meta = {
                "created": time.time(),
                "branch": branch,
                "paths": [str(p) for p in paths if p.exists()],
            }
            (storage / ".locker_meta.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False)
            )
            return key

        shutil.rmtree(storage, ignore_errors=True)
        return None

    def restore(self, key: str) -> bool:
        """Restore a locker and **destroy** it immediately."""
        storage = self.temp_base / key
        if not storage.exists():
            return False

        for item in storage.rglob("*"):
            if item.is_file() and item.name != ".locker_meta.json":
                rel = item.relative_to(storage)
                dest = self.project_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)

        shutil.rmtree(storage, ignore_errors=True)
        return True

    def find_locker_for_branch(self, branch: str) -> Optional[str]:
        """Find the most recent locker tagged for *branch*."""
        best_key: Optional[str] = None
        best_time = 0.0

        for d in self.temp_base.iterdir():
            if not d.is_dir():
                continue
            meta_path = d / ".locker_meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text())
                if meta.get("branch") == branch:
                    created = meta.get("created", 0)
                    if created > best_time:
                        best_time = created
                        best_key = d.name
            except Exception:
                continue
        return best_key

    def list_lockers(self) -> List[Dict]:
        """Return metadata for all current lockers."""
        result = []
        for d in sorted(self.temp_base.iterdir(), key=lambda x: x.stat().st_mtime):
            if not d.is_dir():
                continue
            meta_path = d / ".locker_meta.json"
            info = {"key": d.name}
            if meta_path.exists():
                try:
                    info.update(json.loads(meta_path.read_text()))
                except Exception:
                    pass
            info["size_mb"] = round(
                sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1048576, 2
            )
            result.append(info)
        return result

    # ------------------------------------------------------------------
    # Convenience: auto-discover tool data
    # ------------------------------------------------------------------

    def _scan_data_dirs(self, max_dir_mb: float) -> Dict[Path, int]:
        """Batch-scan all ``tool/*/data/`` sizes with a single ``du`` call."""
        import subprocess
        tool_root = self.project_root / "tool"
        data_dirs = [
            td / "data" for td in tool_root.iterdir()
            if td.is_dir() and (td / "data").exists()
        ]
        if not data_dirs:
            return {}

        try:
            res = subprocess.run(
                ["du", "-sk"] + [str(d) for d in data_dirs],
                capture_output=True, text=True, timeout=10,
            )
            result: Dict[Path, int] = {}
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        result[Path(parts[1])] = int(parts[0]) * 1024
            return result
        except Exception:
            return {}

    def save_tools_data(self, *, branch: str = "",
                        max_dir_mb: float = 50.0) -> Optional[str]:
        """Save ``tool/*/data/`` dirs (skipping those over *max_dir_mb*),
        config files, and any extra ``persistence_dirs`` from tool.json."""
        paths: List[Path] = []
        tool_root = self.project_root / "tool"
        if not tool_root.exists():
            return None

        limit_bytes = int(max_dir_mb * 1048576)
        sizes = self._scan_data_dirs(max_dir_mb)

        for tool_dir in tool_root.iterdir():
            if not tool_dir.is_dir():
                continue

            data_dir = tool_dir / "data"
            if data_dir.exists():
                sz = sizes.get(data_dir, limit_bytes + 1)
                if sz <= limit_bytes and sz > 0:
                    paths.append(data_dir)
                elif sz > limit_bytes:
                    cfg_file = data_dir / "config.json"
                    if cfg_file.exists():
                        paths.append(cfg_file)

            tj = tool_dir / "tool.json"
            if tj.exists():
                try:
                    cfg = json.loads(tj.read_text())
                    for d in cfg.get("persistence_dirs", []):
                        p = tool_dir / d.strip("/")
                        if p.exists():
                            paths.append(p)
                except Exception:
                    pass

        root_data = self.project_root / "data"
        if root_data.exists() and any(root_data.iterdir()):
            paths.append(root_data)

        return self.save(paths, branch=branch)

    # Keep backward-compatible name
    def save_tools_persistence(self) -> Optional[str]:
        return self.save_tools_data()


def get_persistence_manager(project_root: Path) -> GitPersistenceManager:
    return GitPersistenceManager(project_root)
