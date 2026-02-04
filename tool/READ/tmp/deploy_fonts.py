import os
import sys
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tool.FONT.logic.engine import FontManager
import time

def deploy_fonts_from_papers():
    fm = FontManager(project_root)
    
    # Fonts extracted from the research step
    fonts_to_deploy = [
        "Arial-BoldMT", "ArialMT", "Arnhem-Black", "Arnhem-Blond", 
        "Arnhem-BlondItalic", "Arnhem-Bold", "Arnhem-BoldItalic", "Arnhem-Normal",
        "Calibri", "Calibri-Italic", "Helvetica", "Helvetica-Bold", 
        "OpenSans", "Times-Italic", "Times-Roman"
    ]
    
    # Add some manual mappings for common ones
    fm.register_alias("OpenSans", "open-sans")
    fm.register_alias("Helvetica", "helvetica")
    
    print(f"--- Deploying {len(fonts_to_deploy)} fonts to resource/fonts ---")
    
    success_count = 0
    for font in fonts_to_deploy:
        if fm.get_font_path(font):
            print(f"[ALREADY DEPLOYED] {font}")
            success_count += 1
            continue
            
        print(f"\n[DEPLOYING] {font}...")
        if fm.download_from_fontsgeek(font):
            success_count += 1
        else:
            # Try some common variations if direct fails
            if "MT" in font:
                clean_font = font.replace("MT", "")
                print(f"Retrying without MT: {clean_font}")
                if fm.download_from_fontsgeek(clean_font):
                    fm.register_alias(font, clean_font)
                    success_count += 1
            elif "PS" in font:
                clean_font = font.replace("PS", "")
                print(f"Retrying without PS: {clean_font}")
                if fm.download_from_fontsgeek(clean_font):
                    fm.register_alias(font, clean_font)
                    success_count += 1

        time.sleep(1) # Be polite to FontsGeek

    print(f"\nDeployment Summary: {success_count}/{len(fonts_to_deploy)} fonts deployed.")

if __name__ == "__main__":
    deploy_fonts_from_papers()

