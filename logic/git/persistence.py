import os
import shutil
import json
import tempfile
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class GitPersistenceManager:
    """
    Manages persistence of untracked tool directories across Git branch switches.
    Uses a 'locker key' (ID) pattern and maintains a limit of 8 caches.
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.temp_base = Path(tempfile.gettempdir()) / "aitools_git_persistence"
        self.temp_base.mkdir(parents=True, exist_ok=True)
        self.limit = 8

    def _cleanup_old_caches(self):
        """Ensures the number of caches does not exceed the limit. Deletes half if exceeded."""
        caches = sorted([d for d in self.temp_base.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime)
        if len(caches) >= self.limit:
            to_delete = len(caches) // 2
            for i in range(to_delete):
                try:
                    shutil.rmtree(caches[i])
                except: pass

    def _generate_key(self) -> str:
        ts = time.strftime("%Y%m%d_%H%M%S")
        rand = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"{ts}_{rand}"

    def save(self, paths: List[Path]) -> Optional[str]:
        """
        Saves the provided paths into a new temp storage.
        Returns a 'locker key' (ID) if successful.
        """
        if not paths:
            return None

        self._cleanup_old_caches()
        
        key = self._generate_key()
        storage_path = self.temp_base / key
        storage_path.mkdir(parents=True, exist_ok=True)

        found_any = False
        for src_path in paths:
            if not src_path.exists():
                continue
            
            # Preserve relative path structure within the locker
            try:
                rel_to_root = src_path.relative_to(self.project_root)
                dest_path = storage_path / rel_to_root
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                if src_path.is_dir():
                    shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dest_path)
                found_any = True
            except ValueError:
                # Path is outside project root, skip or handle differently
                continue
        
        if found_any:
            return key
        else:
            if storage_path.exists():
                shutil.rmtree(storage_path)
            return None

    def restore(self, key: str):
        """
        Restores the content of a specific 'locker' and deletes it.
        """
        storage_path = self.temp_base / key
        if not storage_path.exists():
            return False

        # Iterate through everything in storage_path and move back
        for item in storage_path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(storage_path)
                dest_path = self.project_root / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)

        # Cleanup this locker
        try:
            shutil.rmtree(storage_path)
        except: pass
        return True

    def save_tools_persistence(self) -> Optional[str]:
        """
        Convenience method to save all directories defined in tools' tool.json.
        """
        all_paths = []
        tool_root = self.project_root / "tool"
        if not tool_root.exists():
            return None

        for tool_dir in tool_root.iterdir():
            if not tool_dir.is_dir():
                continue
            
            tool_json_path = tool_dir / "tool.json"
            if tool_json_path.exists():
                try:
                    with open(tool_json_path, 'r') as f:
                        config = json.load(f)
                        dirs = config.get("persistence_dirs", [])
                        for d in dirs:
                            all_paths.append(tool_dir / d.strip("/"))
                except: pass
        
        return self.save(all_paths)

def get_persistence_manager(project_root: Path) -> GitPersistenceManager:
    return GitPersistenceManager(project_root)
