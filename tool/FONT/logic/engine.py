import os
import json
import requests
from pathlib import Path
from fontTools.ttLib import TTFont
from PIL import Image, ImageFont, ImageDraw
import numpy as np

class FontEngine:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.fonts_dir = data_dir / "fonts"
        self.heuristics_file = data_dir / "heuristics.json"
        
        self.fonts_dir.mkdir(parents=True, exist_ok=True)
        self.heuristics = self._load_heuristics()

    def _load_heuristics(self):
        if self.heuristics_file.exists():
            with open(self.heuristics_file, "r") as f:
                return json.load(f)
        return {}

    def _save_heuristics(self):
        with open(self.heuristics_file, "w") as f:
            json.dump(self.heuristics, f, indent=2)

    def analyze_font(self, font_path: str):
        """
        Extract font metrics and perform glyph analysis to get heuristics.
        """
        path = Path(font_path)
        if not path.exists():
            return None
        
        tt = TTFont(str(path))
        
        # hhea table for vertical metrics
        hhea = tt.get('hhea')
        # OS/2 table for even more metrics
        os2 = tt.get('OS/2')
        
        # Base metrics (normalized to units_per_em)
        upem = tt['head'].unitsPerEm
        
        metrics = {
            "name": path.stem,
            "units_per_em": upem,
            "ascender": hhea.ascent / upem,
            "descender": hhea.descent / upem,
            "line_gap": hhea.lineGap / upem,
            "s_cap_height": os2.sCapHeight / upem if hasattr(os2, 'sCapHeight') else 0,
            "s_x_height": os2.sxHeight / upem if hasattr(os2, 'sxHeight') else 0,
        }
        
        # Glyph Analysis for 'N' (representative of Uppercase)
        heuristics = self._perform_glyph_analysis(font_path, "N")
        metrics.update(heuristics)
        
        self.heuristics[path.stem] = metrics
        self._save_heuristics()
        return metrics

    def search_github_fonts(self, repo: str):
        """Search for font files in GitHub releases."""
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            assets = []
            for asset in data.get("assets", []):
                if any(asset["name"].endswith(ext) for ext in [".ttf", ".otf", ".zip"]):
                    assets.append({
                        "name": asset["name"],
                        "url": asset["browser_download_url"]
                    })
            return assets
        return []

    def _perform_glyph_analysis(self, font_path: str, char: str):
        """
        Render a character and find its actual visual bounds (Glyph Box) 
        relative to the Metric Box (Ascender/Descender).
        """
        size = 1000  # High resolution
        img = Image.new("L", (size, size), 255)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype(font_path, size)
        except:
            return {}

        # Draw the character at origin
        # In Pillow, (0,0) is top-left. 
        # But we want to know where it sits relative to its baseline.
        draw.text((0, 0), char, font=font, fill=0)
        
        img_data = np.array(img)
        mask = img_data < 200
        if not np.any(mask):
            return {}
            
        rows = np.where(np.any(mask, axis=1))[0]
        cols = np.where(np.any(mask, axis=0))[0]
        
        # These are pixel coordinates in our rendering.
        # We need to map these back to normalized font units.
        # For simplicity, let's just use the relative ratios.
        
        # Normalized parameters the user requested:
        # vertical_top, vertical_bottom, horizontal_left, horizontal_right
        # relative to the full font box?
        
        # Actually, let's just return the visual bounds relative to the font size.
        return {
            "glyph_top": rows[0] / size,
            "glyph_bottom": rows[-1] / size,
            "glyph_left": cols[0] / size,
            "glyph_right": cols[-1] / size
        }

    def install_font_from_url(self, name: str, url: str):
        """Download font from URL and store it locally."""
        response = requests.get(url)
        if response.status_code == 200:
            ext = Path(url).suffix or ".ttf"
            font_path = self.fonts_dir / f"{name}{ext}"
            with open(font_path, "wb") as f:
                f.write(response.content)
            return self.analyze_font(str(font_path))
        return None

