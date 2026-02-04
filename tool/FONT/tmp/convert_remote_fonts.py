import sys
import os
from pathlib import Path
import shutil

PROJECT_ROOT = Path("/Applications/AITerminalTools")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tool.FONT.logic.engine import FontManager

def convert_remote_fonts():
    fm = FontManager(PROJECT_ROOT)
    resource_dir = fm.resource_dir
    
    if not resource_dir.exists():
        print(f"Resource directory {resource_dir} not found.")
        return

    print(f"Scanning {resource_dir} for OTF files...")
    
    for font_dir in resource_dir.iterdir():
        if not font_dir.is_dir():
            continue
        
        # Look for any .otf files
        otf_files = list(font_dir.glob("*.otf")) + list(font_dir.glob("*.OTF"))
        
        for otf_path in otf_files:
            # If it's the main font file or another variant
            target_ttf = otf_path.with_suffix(".ttf")
            
            # Special case: if it's the only font file and not named font.ttf, 
            # we might want to name it font.ttf later, but for now just convert.
            
            print(f"Converting {otf_path.relative_to(resource_dir)} to TTF...")
            if fm.convert_otf_to_ttf(otf_path, target_ttf):
                print(f"Successfully converted to {target_ttf.name}")
                otf_path.unlink() # Remove original OTF
                
                # If this was the only file or looks like the main one, ensure font.ttf exists
                if not (font_dir / "font.ttf").exists():
                    shutil.copy(target_ttf, font_dir / "font.ttf")
            else:
                print(f"Failed to convert {otf_path.name}")

    print("Conversion complete.")

if __name__ == "__main__":
    convert_remote_fonts()

