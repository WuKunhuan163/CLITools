import os
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

def log_turing_error(stage: Any, project_root: Optional[Path], tool_name: Optional[str], 
                     exception: Optional[Exception] = None, log_dir: Optional[Path] = None):
    """
    Saves full error information to a log file for a Turing stage failure.
    """
    if not log_dir:
        if project_root and tool_name:
            log_dir = project_root / "tool" / tool_name / "data" / "log"
        else:
            # Fallback to local data/log if project root not available
            log_dir = Path("data/log")
            
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = stage.name.replace("/", "_").replace(" ", "_")
        log_file = log_dir / f"fail_{timestamp}_{safe_name}.log"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Stage: {stage.name}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("-" * 20 + "\n")
            
            if stage.error_brief:
                f.write(f"Brief: {stage.error_brief}\n\n")
            
            if stage.error_full:
                if isinstance(stage.error_full, dict):
                    f.write("Full Context (JSON):\n")
                    f.write(json.dumps(stage.error_full, indent=2))
                else:
                    f.write(f"Full Context:\n{stage.error_full}\n")
                f.write("\n")
                
            if exception:
                f.write("Exception Traceback:\n")
                f.write(traceback.format_exc())
            elif not stage.error_full and not stage.error_brief:
                f.write("No detailed error information captured.\n")
                
        return str(log_file)
    except Exception as e:
        print(f"FATAL ERROR in log_turing_error: {e}")
        return None

