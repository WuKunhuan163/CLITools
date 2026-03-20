import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("/Applications/AITerminalTools")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tool.FONT.logic.engine import FontManager
from tool.FONT.logic.bbox_analyzer import BBoxAnalyzer

def patch_fonts():
    fm = FontManager(PROJECT_ROOT)
    resource_dir = fm.resource_dir
    
    if not resource_dir.exists():
        print(f"Resource directory {resource_dir} not found.")
        return

    for font_dir in resource_dir.iterdir():
        if not font_dir.is_dir():
            continue
        
        ttf_path = font_dir / "font.ttf"
        if not ttf_path.exists():
            # Try to find any ttf/otf
            fonts = list(font_dir.glob("*.ttf")) + list(font_dir.glob("*.otf"))
            if fonts:
                ttf_path = fonts[0]
            else:
                print(f"No font file found in {font_dir}")
                continue
        
        output_dir = font_dir / "bbox_analysis"
        print(f"Patching {font_dir.name}...")
        
        try:
            analyzer = BBoxAnalyzer(ttf_path, output_dir, font_dir.name)
            pdf = analyzer.generate_source_pdf()
            analyzer.analyze(pdf)
            print(f"Successfully patched {font_dir.name}")
        except Exception as e:
            print(f"Failed to patch {font_dir.name}: {e}")

if __name__ == "__main__":
    patch_fonts()

