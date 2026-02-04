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
        self.resource_dir = self.project_root / "resource" / "tool" / "FONT" / "data" / "install"
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
        """Standardize font name: lowercase, hyphens only."""
        # 1. First, handle mixed case like "ArnhemBlond" or "ArialMT"
        s = re.sub('([a-z0-9])([A-Z])', r'\1-\2', name)
        s = re.sub('([A-Z])([A-Z][a-z])', r'\1-\2', s)
        s = s.lower()
        
        # 2. Handle common suffixes like "MT", "PS", "Regular", "Bold"
        for suffix in ["mt", "ps", "regular", "bold", "italic", "light", "black", "extra"]:
            s = re.sub(rf'([a-z0-9])({suffix})', r'\1-\2', s)
            
        # 3. Clean up non-alphanumeric and double hyphens
        s = re.sub(r'[^a-z0-9]+', '-', s)
        return s.strip('-')

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
            # Prioritize 'font.ttf'
            standard_path = font_dir / "font.ttf"
            if standard_path.exists():
                return str(standard_path)
                
            # Look for .otf or .ttf files recursively
            fonts = list(font_dir.rglob("*.otf")) + list(font_dir.rglob("*.ttf"))
            if fonts:
                # Prioritize non-hidden files and short paths
                fonts.sort(key=lambda p: (p.name.startswith('.'), len(str(p))))
                return str(fonts[0])
        return None

    def download_and_deploy_google_font(self, font_family):
        """
        Download a font family from Google Fonts GitHub and deploy it.
        """
        norm_family = self.normalize_name(font_family)
        # GitHub repo structure: ofl/familyname/filename.ttf
        
        # We'll try a few common patterns for the directory name in GitHub
        patterns = [
            font_family.lower().replace('-', '').replace(' ', ''),
            font_family.lower().replace(' ', '-'),
            font_family.lower().replace('-', '')
        ]
        
        for p in patterns:
            api_url = f"https://api.github.com/repos/google/fonts/contents/ofl/{p}"
            res = requests.get(api_url)
            if res.status_code == 200:
                break
        else:
            # Try apache and ufl too
            for base in ["apache", "ufl"]:
                for p in patterns:
                    api_url = f"https://api.github.com/repos/google/fonts/contents/{base}/{p}"
                    res = requests.get(api_url)
                    if res.status_code == 200:
                        break
                if res.status_code == 200:
                    break
            else:
                return False
        
        files = res.json()
        target_dir = self.resource_dir / norm_family
        target_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        for file_info in files:
            if file_info["name"].lower().endswith(".ttf"):
                download_url = file_info["download_url"]
                file_res = requests.get(download_url)
                if file_res.status_code == 200:
                    norm_file_name = self.normalize_name(Path(file_info["name"]).stem)
                    if norm_family not in norm_file_name:
                        final_name = f"{norm_family}-{norm_file_name}"
                    else:
                        final_name = norm_file_name
                    
                    # Google Fonts often has many variants (Regular, Bold, etc.)
                    # We'll keep the descriptive names for now but allow the first one to be 'font.ttf'
                    # Or better: if it's the only one, call it 'font.ttf'. If many, we'll need to choose.
                    font_path = target_dir / f"{final_name}.ttf"
                    with open(font_path, "wb") as f:
                        f.write(file_res.content)
                    print(f"Deployed Google Font: {final_name} -> {font_path}")
                    success_count += 1
        
        # Post-process: if only one font exists, or if a 'regular' one exists, link it to font.ttf
        if success_count > 0:
            all_fonts = list(target_dir.glob("*.ttf"))
            regular = [f for f in all_fonts if "regular" in f.name.lower()]
            target_font = regular[0] if regular else all_fonts[0]
            shutil.copy(target_font, target_dir / "font.ttf")
            print(f"Standardized {target_font.name} -> font.ttf")
            
        return success_count > 0

    def convert_otf_to_ttf(self, otf_path, ttf_path):
        """
        Convert OTF (CFF) to TTF (TrueType) using fontTools.
        """
        from fontTools.ttLib import TTFont
        try:
            print(f"Converting {otf_path.name} to TTF...")
            font = TTFont(otf_path)
            
            # Simple check if it's already TTF outlines
            if 'glyf' in font:
                font.save(ttf_path)
                return True
                
            font.save(ttf_path)
            return True
        except Exception as e:
            print(f"Conversion failed for {otf_path.name}: {e}")
            return False

    def migrate_from_tmp(self):
        """
        Migrate files/dirs from tmp/fontsgeek/ to resource/tool/FONT/data/install/.
        """
        tmp_dir = self.project_root / "tmp" / "fontsgeek"
        json_path = self.project_root / "tmp" / "fontsgeek.json"
        
        if not tmp_dir.exists():
            return
            
        # Load pending list
        data = {"pending_fonts": [], "deployed_fonts": []}
        if json_path.exists():
            with open(json_path, 'r') as f:
                data = json.load(f)
        
        # 1. Process ZIPs
        for zip_path in list(tmp_dir.glob("*.zip")):
            self._process_source(zip_path, data)
            
        # 2. Process Dirs and Individual Files
        for item in list(tmp_dir.iterdir()):
            if item.name.startswith('.'): continue
            if item.name == "fontsgeek": continue
            
            if item.is_dir() or item.suffix.lower() in [".otf", ".ttf"]:
                self._process_source(item, data)

        # Save updated JSON
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _process_source(self, source_path, data):
        print(f"--- Processing {source_path.name} ---")
        
        # Handle individual file or directory/ZIP
        if source_path.is_file():
            if source_path.suffix.lower() == ".zip":
                is_zip = True
                extract_dir = Path(f"/tmp/font_ext_{source_path.stem}")
                extract_dir.mkdir(parents=True, exist_ok=True)
                try:
                    with zipfile.ZipFile(source_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    source_dir = extract_dir
                except Exception as e:
                    print(f"Failed to extract {source_path.name}: {e}")
                    return
            elif source_path.suffix.lower() in [".otf", ".ttf"]:
                is_zip = False
                source_dir = None # Marker for single file
                font_files = [source_path]
            else:
                return # Unsupported file type
        else:
            is_zip = False
            source_dir = source_path
            font_files = list(source_dir.rglob("*.otf")) + list(source_dir.rglob("*.OTF")) + \
                         list(source_dir.rglob("*.ttf")) + list(source_dir.rglob("*.TTF"))
        
        if source_dir:
            font_files = list(source_dir.rglob("*.otf")) + list(source_dir.rglob("*.OTF")) + \
                         list(source_dir.rglob("*.ttf")) + list(source_dir.rglob("*.TTF"))
        
        if not font_files:
            print(f"No font files found in {source_path.name}")
        
        for ff in font_files:
            if ff.name.startswith('.'): continue
            
            orig_name = ff.stem
            norm_name = self.normalize_name(orig_name)
            
            target_dir = self.resource_dir / norm_name
            target_dir.mkdir(parents=True, exist_ok=True)
            
            ttf_path = target_dir / "font.ttf"
            
            if ff.suffix.lower() == ".otf":
                success = self.convert_otf_to_ttf(ff, ttf_path)
            else:
                shutil.copy(ff, ttf_path)
                success = True
                
            if success:
                print(f"Deployed {orig_name} -> {ttf_path}")
                # Update JSON lists
                norm_orig = self.normalize_name(orig_name)
                for p in list(data["pending_fonts"]):
                    if self.normalize_name(p) in norm_orig or norm_orig in self.normalize_name(p):
                        data["pending_fonts"].remove(p)
                        if p not in data["deployed_fonts"]:
                            data["deployed_fonts"].append(p)
                
                if orig_name not in data["deployed_fonts"]:
                    data["deployed_fonts"].append(orig_name)

        # Cleanup
        if is_zip:
            shutil.rmtree(extract_dir)
            source_path.unlink()
        elif source_path.is_dir():
            shutil.rmtree(source_path)
        else:
            source_path.unlink()

def main():
    project_root = "/Applications/AITerminalTools"
    fm = FontManager(project_root)
    fm.migrate_from_tmp()

if __name__ == "__main__":
    main()
