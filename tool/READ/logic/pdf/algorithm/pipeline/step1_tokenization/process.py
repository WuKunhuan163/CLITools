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
        if not heuristics_path.exists():
            parts = norm_name.split('-')
            if parts:
                family = parts[0]
                for d in self.font_resource_dir.iterdir():
                    if d.is_dir() and family in d.name:
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

    def get_background_color(self, image: Image.Image) -> Tuple[int, int, int]:
        img_data = np.array(image.convert("RGB"))
        h, w, _ = img_data.shape
        corners = [img_data[0:10, 0:10], img_data[0:10, w-10:w], img_data[h-10:h, 0:10], img_data[h-10:h, w-10:w]]
        samples = np.concatenate([c.reshape(-1, 3) for c in corners], axis=0)
        return tuple(np.median(samples, axis=0).astype(int))

    def get_token_bboxes(self, spans: List[Dict[str, Any]], zoom: float) -> Tuple[List[List[float]], List[List[float]]]:
        glyph_boxes, actual_boxes = [], []
        for span in spans:
            heuristics = self._get_font_heuristics(span.get("font", "unknown"))
            for char_data in span.get("chars", []):
                if char_data["c"].isspace(): continue
                g_bbox = [c * zoom for c in char_data["bbox"]]
                glyph_boxes.append(g_bbox)
                if heuristics and char_data["c"] in heuristics:
                    h = heuristics[char_data["c"]]
                    gw, gh = g_bbox[2] - g_bbox[0], g_bbox[3] - g_bbox[1]
                    actual_boxes.append([g_bbox[0] + h[0]*gw, g_bbox[1] + h[1]*gh, g_bbox[0] + h[2]*gw, g_bbox[1] + h[3]*gh])
                else:
                    actual_boxes.append(g_bbox)
        return glyph_boxes, actual_boxes

    def wipe_spans(self, image: Image.Image, spans: List[Dict[str, Any]], zoom: float, bg_color=(255, 255, 255)) -> Tuple[Image.Image, np.ndarray]:
        img_data = np.array(image.convert("RGB"))
        h, w, _ = img_data.shape
        mask = np.zeros((h, w), dtype=bool)
        for span in spans:
            heuristics = self._get_font_heuristics(span.get("font", "unknown"))
            for char_data in span.get("chars", []):
                if char_data["c"].isspace(): continue
                g_bbox = [c * zoom for c in char_data["bbox"]]
                w_bbox = None
                if heuristics and char_data["c"] in heuristics:
                    hv = heuristics[char_data["c"]]
                    gw, gh = g_bbox[2] - g_bbox[0], g_bbox[3] - g_bbox[1]
                    w_bbox = [g_bbox[0] + hv[0]*gw, g_bbox[1] + hv[1]*gh, g_bbox[0] + hv[2]*gw, g_bbox[1] + hv[3]*gh]
                else:
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

