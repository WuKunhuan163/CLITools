"""File and directory cleanup utilities."""
import os
import shutil
from pathlib import Path


def cleanup_old_files(target_dir, pattern="*", limit=100, batch_size=None):
    """
    Cleans up old files in a directory if the limit is exceeded.
    Deletes the oldest batch_size files (default: limit // 2).
    """
    try:
        target_path = Path(target_dir)
        if not target_path.exists():
            return
            
        if batch_size is None:
            batch_size = max(1, limit // 2)
            
        files = sorted(list(target_path.glob(pattern)), key=os.path.getmtime)
        if len(files) > limit:
            for i in range(min(len(files), batch_size)):
                try:
                    files[i].unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass


def cleanup_project_patterns(root_dir, patterns=None):
    """
    Recursively delete specified patterns (like .DS_Store, __pycache__) across the project.
    """
    if patterns is None:
        patterns = [".DS_Store", "__pycache__"]
    
    root_path = Path(root_dir)
    for pattern in patterns:
        if pattern == "__pycache__":
            for p in root_path.rglob("__pycache__"):
                if p.is_dir():
                    try: shutil.rmtree(p)
                    except: pass
        else:
            for p in root_path.rglob(pattern):
                try:
                    if p.is_dir(): shutil.rmtree(p)
                    else: p.unlink()
                except: pass
