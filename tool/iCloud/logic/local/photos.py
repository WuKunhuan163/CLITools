import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

class LocalPhotosLibrary:
    def __init__(self, library_path: Path):
        self.library_path = Path(library_path)
        # MacOS Photos Library stores originals here
        self.originals_dir = self.library_path / "originals"
        self._uuid_cache = {} # UUID -> Full Path

    def is_valid(self) -> bool:
        """Returns True if it's a valid macOS .photoslibrary package."""
        return self.originals_dir.exists()

    def find_photo(self, uuid: str) -> Optional[Path]:
        """Finds the original photo path for a given UUID."""
        if uuid in self._uuid_cache:
            return self._uuid_cache[uuid]
            
        if not self.originals_dir.exists():
            return None
            
        # Structure: originals/X/UUID.EXT
        first_char = uuid[0].upper()
        search_dir = self.originals_dir / first_char
        if not search_dir.exists():
            return None
            
        # Glob for the UUID. Extensions can vary (JPG, PNG, MOV, etc.)
        matches = list(search_dir.glob(f"{uuid}.*"))
        if matches:
            self._uuid_cache[uuid] = matches[0]
            return matches[0]
            
        return None

    def fetch_photo(self, photo_id: str, target_path: Path) -> bool:
        """Copies the photo from the local library to the target path."""
        local_path = self.find_photo(photo_id)
        if local_path and local_path.exists():
            try:
                # Ensure target directory exists
                target_path.parent.mkdir(parents=True, exist_ok=True)
                # Copy with metadata preserved
                shutil.copy2(local_path, target_path)
                return True
            except Exception:
                return False
        return False
