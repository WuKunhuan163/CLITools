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

    def find_optimal_offsets(self, img_data: np.ndarray, spans: List[Dict[str, Any]], zoom: float) -> Tuple[float, float]:
        """
        Finds optimal (dx, dy) offsets that minimize pixel intensity within heuristic bboxes.
        """
        best_dx, best_dy = 0, 0
        min_intensity = float('inf')
        h, w, _ = img_data.shape
        search_vals = np.linspace(-1.5, 1.5, 13)
        
        for dy in search_vals:
            for dx in search_vals:
                total_intensity, count = 0, 0
                for span in spans:
                    heuristics = self._get_font_heuristics(span.get("font", "unknown"))
                    if not heuristics: continue
                    for char_data in span.get("chars", []):
                        if char_data["c"].isspace() or char_data["c"] not in heuristics: continue
                        g_bbox = char_data["bbox"]
                        hv = heuristics[char_data["c"]]
                        gw, gh = g_bbox[2] - g_bbox[0], g_bbox[3] - g_bbox[1]
                        ay0, ay1 = int(round((g_bbox[1]+dy+hv[1]*gh)*zoom)), int(round((g_bbox[1]+dy+hv[3]*gh)*zoom))
                        ax0, ax1 = int(round((g_bbox[0]+dx+hv[0]*gw)*zoom)), int(round((g_bbox[0]+dx+hv[2]*gw)*zoom))
                        crop = img_data[max(0, ay0):min(h, ay1), max(0, ax0):min(w, ax1)]
                        if crop.size > 0: total_intensity += np.mean(crop); count += 1
                if count > 0 and total_intensity / count < min_intensity:
                    min_intensity = total_intensity / count
                    best_dx, best_dy = dx, dy
        return float(best_dx), float(best_dy)

    def get_background_color(self, image: Image.Image) -> Tuple[int, int, int]:
        img_data = np.array(image.convert("RGB"))
        h, w, _ = img_data.shape
        corners = [img_data[0:10, 0:10], img_data[0:10, w-10:w], img_data[h-10:h, 0:10], img_data[h-10:h, w-10:w]]
        samples = np.concatenate([c.reshape(-1, 3) for c in corners], axis=0)
        return tuple(np.median(samples, axis=0).astype(int))

    def get_token_bboxes(self, img_data: np.ndarray, spans: List[Dict[str, Any]], zoom: float) -> Tuple[List[List[float]], List[List[float]], Dict[str, float]]:
        glyph_boxes, actual_boxes = [], []
        dx, dy = self.find_optimal_offsets(img_data, spans, zoom)
        for span in spans:
            heuristics = self._get_font_heuristics(span.get("font", "unknown"))
            for char_data in span.get("chars", []):
                if char_data["c"].isspace(): continue
                g_bbox = [c * zoom for c in char_data["bbox"]]
                glyph_boxes.append(g_bbox)
                if heuristics and char_data["c"] in heuristics:
                    h, raw_g = heuristics[char_data["c"]], char_data["bbox"]
                    gw, gh = raw_g[2] - raw_g[0], raw_g[3] - raw_g[1]
                    actual_boxes.append([(raw_g[0]+dx+h[0]*gw)*zoom, (raw_g[1]+dy+h[1]*gh)*zoom, (raw_g[0]+dx+h[2]*gw)*zoom, (raw_g[1]+dy+h[3]*gh)*zoom])
                else: actual_boxes.append(g_bbox)
        return glyph_boxes, actual_boxes, {"dx": dx, "dy": dy}

    def wipe_content(self, image: Image.Image, spans: List[Dict[str, Any]], image_bboxes: List[List[float]], zoom: float, bg_color=(255, 255, 255)) -> Tuple[Image.Image, np.ndarray, Dict[str, float]]:
        img_data = np.array(image.convert("RGB"))
        h, w, _ = img_data.shape
        mask = np.zeros((h, w), dtype=bool)
        dx, dy = self.find_optimal_offsets(img_data, spans, zoom)
        for span in spans:
            heuristics = self._get_font_heuristics(span.get("font", "unknown"))
            for char_data in span.get("chars", []):
                if char_data["c"].isspace(): continue
                g_bbox = [c * zoom for c in char_data["bbox"]]
                if heuristics and char_data["c"] in heuristics:
                    hv, raw_g = heuristics[char_data["c"]], char_data["bbox"]
                    gw, gh = raw_g[2] - raw_g[0], raw_g[3] - raw_g[1]
                    w_box = [(raw_g[0]+dx+hv[0]*gw)*zoom, (raw_g[1]+dy+hv[1]*gh)*zoom, (raw_g[0]+dx+hv[2]*gw)*zoom, (raw_g[1]+dy+hv[3]*gh)*zoom]
                else: w_box = g_bbox
                if w_box:
                    ix0, iy0, ix1, iy1 = [int(round(c)) for c in w_box]
                    y0, y1, x0, x1 = max(0, iy0-1), min(h, iy1+2), max(0, ix0-1), min(w, ix1+2)
                    img_data[y0:y1, x0:x1] = bg_color
                    mask[y0:y1, x0:x1] = True
        for ibox in image_bboxes:
            ix0, iy0, ix1, iy1 = [int(round(c)) for c in ibox]
            y0, y1, x0, x1 = max(0, iy0-2), min(h, iy1+2), max(0, ix0-2), min(w, ix1+2)
            img_data[y0:y1, x0:x1] = bg_color
            mask[y0:y1, x0:x1] = True
        return Image.fromarray(img_data), mask, {"dx": dx, "dy": dy}

    def detect_artifacts(self, original: Image.Image, wiped: Image.Image, bg_color: Tuple[int, int, int]) -> List[Tuple[int, int, int, int]]:
        from scipy.ndimage import label, binary_dilation, binary_erosion
        w_data = np.array(wiped.convert("RGB")).astype(float)
        diff = np.abs(w_data - np.full_like(w_data, bg_color))
        mask = np.any(diff > 30, axis=2)
        if mask.ndim != 2: return []
        
        # Line detection enhancement: keep thin lines by not opening strictly with 2x2
        # Instead, use directional filters to strengthen lines
        h_line = binary_dilation(binary_erosion(mask, structure=np.ones((1, 15))), structure=np.ones((1, 15)))
        v_line = binary_dilation(binary_erosion(mask, structure=np.ones((15, 1))), structure=np.ones((15, 1)))
        
        # Combine original with strengthened lines
        enhanced_mask = mask | h_line | v_line
        
        labeled, num = label(enhanced_mask)
        bboxes = []
        for i in range(1, num + 1):
            m = (labeled == i)
            r, c = np.where(np.any(m, axis=1))[0], np.where(np.any(m, axis=0))[0]
            if len(r) > 0 and len(c) > 0:
                width, height = len(c), len(r)
                if (width * height >= 40) or (width > 50) or (height > 50):
                    bboxes.append((int(c[0]), int(r[0]), int(c[-1]), int(r[-1])))
        return bboxes

    def join_tokens(self, char_bboxes: List[List[float]], image_bboxes: List[List[float]], artifact_bboxes: List[Tuple[int, int, int, int]]) -> List[Dict[str, Any]]:
        """
        Final stage of tokenization: join characters into words and images into clusters.
        """
        tokens = []
        for i, abox in enumerate(artifact_bboxes): tokens.append({"type": "artifact", "bbox": list(abox), "id": f"A{i+1}"})
        for i, ibox in enumerate(image_bboxes): tokens.append({"type": "image", "bbox": list(ibox), "id": f"I{i+1}"})
        for i, tbox in enumerate(char_bboxes): tokens.append({"type": "text", "bbox": list(tbox), "id": f"T{i+1}"})
        return tokens
