import os
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
from typing import List, Dict, Any, Tuple

class TextWiper:
    """
    Handles erasing text from background images using font-specific heuristics.
    """
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.font_resource_dir = self.project_root / "resource" / "tool" / "FONT" / "data" / "install"
        self.missing_fonts_log = self.project_root / "tmp" / "missing_fonts.json"
        self.font_cache = {}
        self.missing_fonts = self._load_missing_fonts()

    def _load_missing_fonts(self):
        if self.missing_fonts_log.exists():
            try:
                with open(self.missing_fonts_log, 'r') as f:
                    return set(json.load(f))
            except: pass
        return set()

    def _save_missing_fonts(self):
        self.missing_fonts_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.missing_fonts_log, 'w') as f:
            json.dump(sorted(list(self.missing_fonts)), f, indent=2)

    def _normalize_font_name(self, name: str):
        # 1. First, handle mixed case like "ArnhemBlond" or "ArialMT"
        import re
        s = re.sub('([a-z0-9])([A-Z])', r'\1-\2', name)
        s = re.sub('([A-Z])([A-Z][a-z])', r'\1-\2', s)
        s = s.lower()
        
        # 2. Handle common suffixes like "MT", "PS", "Regular", "Bold"
        for suffix in ["mt", "ps", "regular", "bold", "italic", "light", "black", "extra"]:
            s = re.sub(rf'([a-z0-9])({suffix})', r'\1-\2', s)
            
        # 3. Clean up non-alphanumeric and double hyphens
        s = re.sub(r'[^a-z0-9]+', '-', s)
        return s.strip('-')

    def _get_font_heuristics(self, font_name: str):
        if font_name in self.font_cache:
            return self.font_cache[font_name]

        norm_name = self._normalize_font_name(font_name)
        
        # Try exact match first
        heuristics_path = self.font_resource_dir / norm_name / "info.json"
        
        # Fallback search: check for partial matches or aliases
        if not heuristics_path.exists():
            parts = norm_name.split('-')
            # Look for the family name (usually the first part)
            if parts:
                family = parts[0]
                for d in self.font_resource_dir.iterdir():
                    if not d.is_dir(): continue
                    # If the folder name contains the family name
                    if family in d.name:
                        test_path = d / "info.json"
                        if test_path.exists():
                            heuristics_path = test_path
                            break
        
        if heuristics_path and heuristics_path.exists():
            try:
                with open(heuristics_path, 'r') as f:
                    data = json.load(f)
                    self.font_cache[font_name] = data.get("heuristics", {})
                    # If we matched, remove from missing fonts if it was there
                    if font_name in self.missing_fonts:
                        self.missing_fonts.remove(font_name)
                        self._save_missing_fonts()
                    return self.font_cache[font_name]
            except: pass
        
        if font_name not in self.missing_fonts:
            self.missing_fonts.add(font_name)
            self._save_missing_fonts()
        
        self.font_cache[font_name] = None
        return None

    def wipe_spans(self, image: Image.Image, spans: List[Dict[str, Any]], zoom: float, bg_color=(255, 255, 255)) -> Tuple[Image.Image, np.ndarray]:
        """
        Wipe text spans from the image.
        Uses actual bboxes from heuristics if available, otherwise tight glyph bboxes.
        Returns (wiped_image, content_mask).
        """
        img_data = np.array(image.convert("RGB"))
        h, w, _ = img_data.shape
        content_mask = np.zeros((h, w), dtype=bool)
        
        for span in spans:
            font_name = span.get("font", "unknown")
            heuristics = self._get_font_heuristics(font_name)
            
            for char_data in span.get("chars", []):
                char = char_data["c"]
                if char.isspace(): continue
                
                g_bbox = [c * zoom for c in char_data["bbox"]]
                
                wipe_bbox = None
                if heuristics and char in heuristics:
                    h_vals = heuristics[char] # [l, t, r, b] normalized to glyph bbox
                    gw = g_bbox[2] - g_bbox[0]
                    gh = g_bbox[3] - g_bbox[1]
                    
                    wipe_bbox = [
                        g_bbox[0] + h_vals[0] * gw,
                        g_bbox[1] + h_vals[1] * gh,
                        g_bbox[0] + h_vals[2] * gw,
                        g_bbox[1] + h_vals[3] * gh
                    ]
                else:
                    # Fallback: find tight dark pixels within glyph bbox
                    x0, y0, x1, y1 = [int(round(c)) for c in g_bbox]
                    x0, y0 = max(0, x0-1), max(0, y0-1)
                    x1, y1 = min(w, x1+1), min(h, y1+1)
                    
                    if x1 <= x0 or y1 <= y0: continue
                    
                    region = img_data[y0:y1, x0:x1]
                    gray = np.mean(region, axis=2)
                    mask = gray < 200 # Content pixels
                    
                    if np.any(mask):
                        rows = np.where(np.any(mask, axis=1))[0]
                        cols = np.where(np.any(mask, axis=0))[0]
                        # We use 1px padding
                        p = 1
                        wipe_bbox = [
                            x0 + cols[0] - p,
                            y0 + rows[0] - p,
                            x0 + cols[-1] + p,
                            y0 + rows[-1] + p
                        ]
                
                if wipe_bbox:
                    wx0, wy0, wx1, wy1 = [int(round(c)) for c in wipe_bbox]
                    y_start, y_end = max(0, wy0), min(h, wy1+1)
                    x_start, x_end = max(0, wx0), min(w, wx1+1)
                    img_data[y_start:y_end, x_start:x_end] = bg_color
                    content_mask[y_start:y_end, x_start:x_end] = True
        
        return Image.fromarray(img_data), content_mask

