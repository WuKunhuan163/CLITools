#!/usr/bin/env python3
import time
import os
import json
import traceback
from typing import Optional
from pathlib import Path
from logic.turing.logic import TuringStage

def log_turing_error(stage: TuringStage, project_root: Optional[Path], 
                     tool_name: Optional[str], exception: Optional[Exception] = None,
                     log_dir: Optional[Path] = None,
                     session_logger: Optional['SessionLogger'] = None):
    """Saves full error information to the session log (preferred) or a standalone file.
    
    If a session_logger is provided, appends to the current session log.
    Otherwise falls back to creating a standalone log_*.log file."""
    
    full_info = stage.error_full or stage.error_brief or (str(exception) if exception else "No detailed error message provided.")
    if isinstance(full_info, dict):
        full_info = json.dumps(full_info, indent=2)
    elif not isinstance(full_info, str):
        full_info = str(full_info)
    if exception:
        full_info += "\n\nTraceback:\n" + "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    if stage.captured_output:
        full_info += "\n\nCaptured Command Output:\n" + "-" * 20 + "\n" + stage.captured_output + "\n" + "-" * 20

    if session_logger:
        session_logger.write(
            f"TURING_ERROR stage={stage.name}",
            extra=full_info,
            include_stack=False
        )
        return str(session_logger.path)

    if not log_dir:
        if not project_root or not tool_name: return None
        if tool_name != "TOOL":
            log_dir = project_root / "tool" / tool_name / "data" / "log"
        else:
            log_dir = project_root / "data" / "log"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    ts = time.strftime("%Y%m%d_%H%M%S")
    task_suffix = f"_{stage.name.replace(' ', '_')}" if stage.name else ""
    log_file = log_dir / f"log_{ts}{task_suffix}.log"
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Stage: {stage.name}\n")
            f.write(f"Timestamp: {ts}\n")
            f.write("-" * 20 + "\n")
            f.write(full_info)
            f.flush()
            try: os.fsync(f.fileno())
            except: pass
        
        from logic.utils import cleanup_old_files
        try: cleanup_old_files(log_dir, "log_*.log", limit=64)
        except: pass
            
        return str(log_file)
    except Exception:
        return None
