import json
import os
from pathlib import Path

class AuditManager:
    """
    Manages audit/cache files for various components.
    Unified logic for caching and warning users.
    """
    def __init__(self, audit_dir, component_name=None, audit_command=None):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.component_name = component_name
        self.audit_command = audit_command

    def get_path(self, name):
        if not name.endswith(".json"):
            name = f"{name}.json"
        return self.audit_dir / name

    def load(self, name):
        path = self.get_path(name)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save(self, name, data):
        path = self.get_path(name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def print_cache_warning(self, data_type=None, custom_command=None, silent=False):
        """Prints a standardized warning when cache is used."""
        if silent:
            return
            
        from logic.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        YELLOW = get_color("YELLOW", "\033[33m")
        RESET = get_color("RESET", "\033[0m")
        
        warning_label = f"{BOLD}{YELLOW}Warning{RESET}"
        type_str = f" {data_type}" if data_type else ""
        
        # Build the cleanup command
        cmd = custom_command or self.audit_command
        refresh_msg = ""
        if cmd:
            # Check if cmd already starts with PYTHON or TOOL, if not assume it's a relative script
            refresh_msg = f" To force refresh, run: rm -rf {self.audit_dir} && {cmd}"
        else:
            refresh_msg = f" To force refresh, clear the cache directory: {self.audit_dir}"
            
        import sys
        # Clear current erasable line if any
        sys.stdout.write("\r\033[K")
        print(f"{warning_label}: Using cached{type_str} data.{refresh_msg}")

class AuditBase:
    """
    Base class for tools that involve heavy audit operations.
    Supports --force option to automatically clear cache.
    """
    def __init__(self, audit_mgr):
        self.audit_mgr = audit_mgr

    def handle_force(self, args):
        """If args.force is true, clear the cache directory."""
        if getattr(args, 'force', False):
            if self.audit_mgr.audit_dir.exists():
                import shutil
                shutil.rmtree(self.audit_mgr.audit_dir)
                self.audit_mgr.audit_dir.mkdir(parents=True, exist_ok=True)
            return True
        return False

