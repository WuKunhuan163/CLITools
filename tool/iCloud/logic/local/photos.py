import os
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class LocalPhotosLibrary:
    def __init__(self, library_path: Path):
        self.library_path = Path(library_path)
        self.db_path = self.library_path / "database" / "Photos.sqlite"
        self.originals_dir = self.library_path / "originals"
        self._mapping_cache = {} # iCloudID -> (LocalUUID, Extension, LocalCreationDate)
        self._db_conn = None

    def __del__(self):
        self.close()

    def close(self):
        if self._db_conn:
            try: self._db_conn.close()
            except: pass
            self._db_conn = None

    def is_valid(self) -> bool:
        """Returns True if it's a valid macOS .photoslibrary package."""
        return self.db_path.exists() and self.originals_dir.exists()

    def _get_conn(self):
        if not self._db_conn:
            # Connect in read-only mode
            self._db_conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        return self._db_conn

    def _load_info_from_db(self, icloud_id: str) -> Optional[tuple]:
        """Queries the sqlite database for photo info."""
        if not self.db_path.exists():
            return None
            
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Fetch UUID, Filename (for extension), Created Date and Timezone Offset
            query = """
                SELECT a.ZUUID, a.ZFILENAME, a.ZDATECREATED, aa.ZTIMEZONEOFFSET
                FROM ZASSET a
                JOIN ZADDITIONALASSETATTRIBUTES aa ON a.Z_PK = aa.ZASSET
                WHERE aa.ZORIGINALSTABLEHASH = ?
            """
            cursor.execute(query, (icloud_id,))
            result = cursor.fetchone()
            
            if result:
                uuid, filename, apple_ts, tz_offset = result
                ext = os.path.splitext(filename)[1] if filename else ".jpeg"
                
                # Apple epoch is Jan 1, 2001
                dt_utc = datetime(2001, 1, 1) + timedelta(seconds=apple_ts)
                
                local_dt = dt_utc
                if tz_offset is not None:
                    local_dt = dt_utc + timedelta(seconds=tz_offset)
                
                return uuid, ext, local_dt
        except Exception:
            self.close() # Reset on error
        return None

    def preload_mappings(self, icloud_ids: List[str]):
        """Bulk loads mappings into the cache."""
        if not self.db_path.exists() or not icloud_ids:
            return
            
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Process in batches of 999 (SQLite limit for IN clause)
            for i in range(0, len(icloud_ids), 999):
                batch = icloud_ids[i:i+999]
                placeholders = ",".join(["?"] * len(batch))
                query = f"""
                    SELECT aa.ZORIGINALSTABLEHASH, a.ZUUID, a.ZFILENAME, a.ZDATECREATED, aa.ZTIMEZONEOFFSET
                    FROM ZASSET a
                    JOIN ZADDITIONALASSETATTRIBUTES aa ON a.Z_PK = aa.ZASSET
                    WHERE aa.ZORIGINALSTABLEHASH IN ({placeholders})
                """
                cursor.execute(query, batch)
                for row in cursor.fetchall():
                    icloud_id, uuid, filename, apple_ts, tz_offset = row
                    ext = os.path.splitext(filename)[1] if filename else ".jpeg"
                    dt_utc = datetime(2001, 1, 1) + timedelta(seconds=apple_ts)
                    local_dt = dt_utc
                    if tz_offset is not None:
                        local_dt = dt_utc + timedelta(seconds=tz_offset)
                    self._mapping_cache[icloud_id] = (uuid, ext, local_dt)
        except Exception:
            self.close()

    def find_photo(self, icloud_id: str, filename: Optional[str] = None, created_dt: Optional[datetime] = None) -> Optional[tuple]:
        """Finds the original photo path and local creation date for an iCloud ID."""
        if icloud_id in self._mapping_cache:
            uuid, ext, local_dt = self._mapping_cache[icloud_id]
        else:
            res = self._load_info_from_db(icloud_id)
            if not res:
                # Try fallback by filename and date if provided
                if filename and created_dt:
                    res = self._lookup_by_filename_and_date(filename, created_dt)
                
                if not res:
                    return None
                    
            uuid, ext, local_dt = res
            self._mapping_cache[icloud_id] = (uuid, ext, local_dt)
            
        # Structure: originals/X/UUID.EXT
        first_char = uuid[0].upper()
        search_dir = self.originals_dir / first_char
        if not search_dir.exists():
            return None
            
        local_path = search_dir / f"{uuid}{ext}"
        if not local_path.exists():
            matches = list(search_dir.glob(f"{uuid}.*"))
            if matches:
                local_path = matches[0]
            else:
                return None
                
        return local_path, local_dt

    def _lookup_by_filename_and_date(self, filename: str, created_dt: datetime) -> Optional[tuple]:
        """Fallback lookup by filename and creation date (allowing for small drift)."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Apple timestamps are in seconds since 2001-01-01
            apple_epoch = datetime(2001, 1, 1)
            # We don't know the exact timezone offset used in DB for this asset yet,
            # but usually ZDATECREATED is UTC.
            # iCloud created_dt is also UTC.
            target_ts = (created_dt - apple_epoch).total_seconds()
            
            # Search within 10 seconds window and matching filename
            query = """
                SELECT ZUUID, ZFILENAME, ZDATECREATED
                FROM ZASSET 
                WHERE ZFILENAME = ? AND ZDATECREATED >= ? AND ZDATECREATED <= ?
            """
            cursor.execute(query, (filename, target_ts - 5, target_ts + 5))
            result = cursor.fetchone()
            if result:
                uuid, fname, apple_ts = result
                ext = os.path.splitext(fname)[1] if fname else os.path.splitext(filename)[1]
                # For fallback, we just return the UTC date
                local_dt = apple_epoch + timedelta(seconds=apple_ts)
                return uuid, ext, local_dt
        except Exception:
            self.close()
        return None

    def fetch_photo(self, icloud_id: str, target_path: Path) -> Optional[datetime]:
        """Copies the photo and returns the local creation date if found."""
        res = self.find_photo(icloud_id)
        if res:
            local_path, local_dt = res
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_path, target_path)
                return local_dt
            except Exception:
                return None
        return None
