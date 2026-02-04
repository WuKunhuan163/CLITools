import os
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Tuple

class Preprocessor:
    """
    Handles PDF page preprocessing: background detection, text wiping, and artifact discovery.
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
        import re
        s = re.sub('([a-z0-9])([A-Z])', r'\1-\2', name)
        s = re.sub('([A-Z])([A-Z][a-z])', r'\1-\2', s)
        s = s.lower()
        for suffix in ["mt", "ps", "regular", "bold", "italic", "light", "black", "extra"]:
            s = re.sub(rf'([a-z0-9])({suffix})', r'\1-\2', s)
        s = re.sub(r'[^a-z0-9]+', '-', s)
        return s.strip('-')

    def _get_font_heuristics(self, font_name: str):
        if font_name in self.font_cache:
            return self.font_cache[font_name]
        norm_name = self._normalize_font_name(font_name)
        heuristics_path = self.font_resource_dir / norm_name / "info.json"
        
        # Stricter fallback: prevent matching Regular/Blond to Italic
        if not heuristics_path.exists():
            parts = norm_name.split('-')
            if parts:
                family = parts[0]
                for d in self.font_resource_dir.iterdir():
                    if d.is_dir() and family in d.name:
                        # Check for italic/bold consistency
                        if ("italic" in norm_name) != ("italic" in d.name): continue
                        if ("bold" in norm_name) != ("bold" in d.name): continue
                        test_path = d / "info.json"
                        if test_path.exists():
                            heuristics_path = test_path; break
        
        if heuristics_path and heuristics_path.exists():
            try:
                with open(heuristics_path, 'r') as f:
                    data = json.load(f)
                    self.font_cache[font_name] = data.get("heuristics", {})
                    if font_name in self.missing_fonts:
                        self.missing_fonts.remove(font_name); self._save_missing_fonts()
                    return self.font_cache[font_name]
            except: pass
        if font_name not in self.missing_fonts:
            self.missing_fonts.add(font_name); self._save_missing_fonts()
        self.font_cache[font_name] = None
        return None

    def find_optimal_v_offset(self, img_data: np.ndarray, spans: List[Dict[str, Any]], zoom: float) -> float:
        """
        Finds a vertical offset (dy) that minimizes pixel intensity within heuristic bboxes.
        """
        best_dy = 0
        min_intensity = float('inf')
        h, w, _ = img_data.shape
        
        # Test range: -2 to 2 points
        for dy in np.linspace(-2, 2, 21):
            total_intensity = 0
            count = 0
            for span in spans:
                heuristics = self._get_font_heuristics(span.get("font", "unknown"))
                if not heuristics: continue
                for char_data in span.get("chars", []):
                    char = char_data["c"]
                    if char.isspace() or char not in heuristics: continue
                    g_bbox = [c for c in char_data["bbox"]]
                    hv = heuristics[char]
                    gw, gh = g_bbox[2] - g_bbox[0], g_bbox[3] - g_bbox[1]
                    
                    ay0 = int(round((g_bbox[1] + dy + hv[1]*gh) * zoom))
                    ay1 = int(round((g_bbox[1] + dy + hv[3]*gh) * zoom))
                    ax0 = int(round((g_bbox[0] + hv[0]*gw) * zoom))
                    ax1 = int(round((g_bbox[0] + hv[2]*gw) * zoom))
                    
                    crop = img_data[max(0, ay0):min(h, ay1), max(0, ax0):min(w, ax1)]
                    if crop.size > 0:
                        total_intensity += np.mean(crop)
                        count += 1
            if count > 0 and total_intensity / count < min_intensity:
                min_intensity = total_intensity / count
                best_dy = dy
        return best_dy

    def get_background_color(self, image: Image.Image) -> Tuple[int, int, int]:
        img_data = np.array(image.convert("RGB"))
        h, w, _ = img_data.shape
        corners = [img_data[0:10, 0:10], img_data[0:10, w-10:w], img_data[h-10:h, 0:10], img_data[h-10:h, w-10:w]]
        samples = np.concatenate([c.reshape(-1, 3) for c in corners], axis=0)
        return tuple(np.median(samples, axis=0).astype(int))

    def get_token_bboxes(self, img_data: np.ndarray, spans: List[Dict[str, Any]], zoom: float) -> Tuple[List[List[float]], List[List[float]]]:
        glyph_boxes, actual_boxes = [], []
        
        # Calculate global vertical offset to align heuristics with actual pixels
        dy = self.find_optimal_v_offset(img_data, spans, zoom)
        
        for span in spans:
            heuristics = self._get_font_heuristics(span.get("font", "unknown"))
            for char_data in span.get("chars", []):
                if char_data["c"].isspace(): continue
                g_bbox = [c * zoom for c in char_data["bbox"]]
                glyph_boxes.append(g_bbox)
                
                if heuristics and char_data["c"] in heuristics:
                    h = heuristics[char_data["c"]]
                    # Raw bbox points (not zoomed) for offset application
                    raw_g = char_data["bbox"]
                    gw, gh = raw_g[2] - raw_g[0], raw_g[3] - raw_g[1]
                    actual_boxes.append([
                        (raw_g[0] + h[0]*gw) * zoom,
                        (raw_g[1] + dy + h[1]*gh) * zoom,
                        (raw_g[0] + h[2]*gw) * zoom,
                        (raw_g[1] + dy + h[3]*gh) * zoom
                    ])
                else:
                    actual_boxes.append(g_bbox)
        return glyph_boxes, actual_boxes

    def wipe_spans(self, image: Image.Image, spans: List[Dict[str, Any]], zoom: float, bg_color=(255, 255, 255)) -> Tuple[Image.Image, np.ndarray]:
        img_data = np.array(image.convert("RGB"))
        h, w, _ = img_data.shape
        mask = np.zeros((h, w), dtype=bool)
        
        # Calculate optimal offset for wiping as well
        dy = self.find_optimal_v_offset(img_data, spans, zoom)
        
        for span in spans:
            heuristics = self._get_font_heuristics(span.get("font", "unknown"))
            for char_data in span.get("chars", []):
                if char_data["c"].isspace(): continue
                g_bbox = [c * zoom for c in char_data["bbox"]]
                w_bbox = None
                if heuristics and char_data["c"] in heuristics:
                    hv = heuristics[char_data["c"]]
                    raw_g = char_data["bbox"]
                    gw, gh = raw_g[2] - raw_g[0], raw_g[3] - raw_g[1]
                    w_bbox = [
                        (raw_g[0] + hv[0]*gw) * zoom,
                        (raw_g[1] + dy + hv[1]*gh) * zoom,
                        (raw_g[0] + hv[2]*gw) * zoom,
                        (raw_g[1] + dy + hv[3]*gh) * zoom
                    ]
                else:
                    # Fallback tight pixel mask check
                    ix0, iy0, ix1, iy1 = [int(round(c)) for c in g_bbox]
                    crop = img_data[max(0, iy0-1):min(h, iy1+1), max(0, ix0-1):min(w, ix1+1)]
                    if crop.size > 0 and np.any(np.mean(crop, axis=2) < 200):
                        m = np.mean(crop, axis=2) < 200
                        r, c = np.where(m)
                        w_bbox = [ix0-1+c[0]-1, iy0-1+r[0]-1, ix0-1+c[-1]+1, iy0-1+r[-1]+1]
                if w_bbox:
                    wx0, wy0, wx1, wy1 = [int(round(c)) for c in w_bbox]
                    y0, y1, x0, x1 = max(0, wy0), min(h, wy1+1), max(0, wx0), min(w, wx1+1)
                    img_data[y0:y1, x0:x1] = bg_color
                    mask[y0:y1, x0:x1] = True
        return Image.fromarray(img_data), mask

    def detect_artifacts(self, original: Image.Image, wiped: Image.Image, bg_color: Tuple[int, int, int]) -> List[Tuple[int, int, int, int]]:
        from scipy.ndimage import label
        w_data = np.array(wiped.convert("RGB")).astype(float)
        diff = np.abs(w_data - np.full_like(w_data, bg_color))
        mask = np.any(diff > 30, axis=2)
        if mask.ndim != 2: return []
        labeled, num = label(mask)
        bboxes = []
        for i in range(1, num + 1):
            m = (labeled == i)
            r, c = np.where(np.any(m, axis=1))[0], np.where(np.any(m, axis=0))[0]
            if len(r) > 0 and len(c) > 0 and len(r)*len(c) >= 20:
                bboxes.append((int(c[0]), int(r[0]), int(c[-1]), int(r[-1])))
        return bboxes

