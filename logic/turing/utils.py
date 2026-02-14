#!/usr/bin/env python3
import sys
import time
import os
import json
import traceback
from typing import Optional
from pathlib import Path
from logic.turing.logic import TuringStage

def log_turing_error(stage: TuringStage, project_root: Optional[Path], 
                     tool_name: Optional[str], exception: Optional[Exception] = None,
                     log_dir: Optional[Path] = None):
    """Saves full error information to a log file."""
    if not log_dir:
        if not project_root or not tool_name: return None
        
        # Fallback to legacy flat structure if log_dir not provided
        if tool_name != "TOOL":
            log_dir = project_root / "tool" / tool_name / "data" / "log"
        else:
            log_dir = project_root / "data" / "log"
    
    # print(f"DEBUG: log_turing_error log_dir={log_dir}", file=sys.stderr)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    ts = time.strftime("%Y%m%d_%H%M%S")
    # Use task ID if available to distinguish between parallel tasks
    task_suffix = f"_{stage.name.replace(' ', '_')}" if stage.name else ""
    log_file = log_dir / f"fail_{ts}{task_suffix}.log"
    
    # Prioritize error_full as it may contain the verification history
    full_info = stage.error_full or (str(exception) if exception else "No detailed error message provided.")
    if isinstance(full_info, dict):
        full_info = json.dumps(full_info, indent=2)
    elif not isinstance(full_info, str):
        full_info = str(full_info)
        
    if exception:
        full_info += "\n\nTraceback:\n" + "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        
    if stage.captured_output:
        full_info += "\n\nCaptured Command Output:\n" + "=" * 20 + "\n" + stage.captured_output + "\n" + "=" * 20
        
    try:
        # Check if log_dir exists or can be created
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Stage: {stage.name}\n")
            f.write(f"Timestamp: {ts}\n")
            f.write("-" * 20 + "\n")
            f.write(full_info)
            f.flush()
            # Some environments might not support fsync on all FDs
            try:
                os.fsync(f.fileno())
            except:
                pass
        
        # Basic cleanup (limit 100 logs)
        from logic.utils import cleanup_old_files
        try:
            cleanup_old_files(log_dir, "fail_*.log", limit=100)
        except:
            pass
            
        return str(log_file)
    except Exception:
        return None

