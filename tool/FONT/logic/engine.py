import os
import sys
import json
import requests
import zipfile
import shutil
import re
import subprocess
from pathlib import Path

class FontManager:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.resource_dir = self.project_root / "resource" / "fonts"
        self.mapping_file = self.project_root / "tool" / "FONT" / "logic" / "font_mapping.json"
        self.mappings = self._load_mappings()

    def _load_mappings(self):
        if self.mapping_file.exists():
            with open(self.mapping_file, 'r') as f:
                return json.load(f)
        return {
            "aliases": {},
            "metadata": {}
        }

    def _save_mappings(self):
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.mapping_file, 'w') as f:
            json.dump(self.mappings, f, indent=2)

    def normalize_name(self, name):
        """Standardize font name: lowercase, no special chars."""
        return re.sub(r'[^a-z0-9]+', '', name.lower())

    def register_alias(self, alias, target_name):
        norm_alias = self.normalize_name(alias)
        norm_target = self.normalize_name(target_name)
        self.mappings["aliases"][norm_alias] = norm_target
        self._save_mappings()

    def get_font_path(self, font_name):
        norm_name = self.normalize_name(font_name)
        target_name = self.mappings["aliases"].get(norm_name, norm_name)
        
        # Search in resource directory
        font_dir = self.resource_dir / target_name
        if font_dir.exists():
            # Look for .otf or .ttf files recursively
            fonts = list(font_dir.rglob("*.otf")) + list(font_dir.rglob("*.ttf"))
            if fonts:
                # Prioritize non-hidden files and short paths
                fonts.sort(key=lambda p: (p.name.startswith('.'), len(str(p))))
                return str(fonts[0])
        return None

    def migrate_from_tmp(self):
        """
        Migrate ZIP files from tmp/fontsgeek/ to resource/fonts/.
        """
        tmp_dir = self.project_root / "tmp" / "fontsgeek"
        json_path = self.project_root / "tmp" / "fontsgeek.json"
        
        if not tmp_dir.exists():
            print(f"Directory {tmp_dir} not found.")
            return
            
        # Load pending list
        data = {"pending_fonts": [], "deployed_fonts": []}
        if json_path.exists():
            with open(json_path, 'r') as f:
                data = json.load(f)
        
        zips = list(tmp_dir.glob("*.zip"))
        if not zips:
            print("No ZIP files found in tmp/fontsgeek/.")
            return

        for zip_path in zips:
            print(f"--- Processing {zip_path.name} ---")
            # Try to identify the font from the filename
            # structure: name_random.zip
            base_name = zip_path.stem.split('_')[0]
            norm_target = self.normalize_name(base_name)
            
            # Look for matches in pending_fonts
            matched_font = None
            for f_name in data["pending_fonts"]:
                if self.normalize_name(f_name) == norm_target:
                    matched_font = f_name
                    break
            
            # If no exact match, just use the base name
            target_font_name = matched_font or base_name
            norm_name = self.normalize_name(target_font_name)
            
            target_dir = self.resource_dir / norm_name
            target_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(target_dir)
                
                print(f"Successfully migrated {target_font_name} to {target_dir}")
                
                # Cleanup
                zip_path.unlink()
                
                # Update JSON
                if matched_font and matched_font in data["pending_fonts"]:
                    data["pending_fonts"].remove(matched_font)
                if target_font_name not in data["deployed_fonts"]:
                    data["deployed_fonts"].append(target_font_name)
                    
            except Exception as e:
                print(f"Failed to migrate {zip_path.name}: {e}")

        # Save updated JSON
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

def main():
    # Example usage for research
    project_root = "/Applications/AITerminalTools"
    fm = FontManager(project_root)
    
    # Test with Arnhem-Blond (already have it, but for logic test)
    # fm.download_from_fontsgeek("Arnhem-Blond")

if __name__ == "__main__":
    main()
