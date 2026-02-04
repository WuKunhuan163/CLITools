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
                with open(self.missing_fonts_log, 'r') as f: return set(json.load(f))
            except: pass
        return set()

    def _save_missing_fonts(self):
        self.missing_fonts_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.missing_fonts_log, 'w') as f: json.dump(sorted(list(self.missing_fonts)), f, indent=2)

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
        if font_name in self.font_cache: return self.font_cache[font_name]
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
                        if test_path.exists(): heuristics_path = test_path; break
        if heuristics_path and heuristics_path.exists():
            try:
                with open(heuristics_path, 'r') as f:
                    data = json.load(f)
                    self.font_cache[font_name] = data.get("heuristics", {})
                    if font_name in self.missing_fonts: self.missing_fonts.remove(font_name); self._save_missing_fonts()
                    return self.font_cache[font_name]
            except: pass
        if font_name not in self.missing_fonts: self.missing_fonts.add(font_name); self._save_missing_fonts()
        self.font_cache[font_name] = None
        return None

    def find_optimal_offsets(self, img_data: np.ndarray, spans: List[Dict[str, Any]], zoom: float) -> Tuple[float, float]:
        best_dx, best_dy, min_intensity = 0, 0, float('inf')
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
                        g_bbox, hv = char_data["bbox"], heuristics[char_data["c"]]
                        gw, gh = g_bbox[2] - g_bbox[0], g_bbox[3] - g_bbox[1]
                        ay0, ay1 = int(round((g_bbox[1]+dy+hv[1]*gh)*zoom)), int(round((g_bbox[1]+dy+hv[3]*gh)*zoom))
                        ax0, ax1 = int(round((g_bbox[0]+dx+hv[0]*gw)*zoom)), int(round((g_bbox[0]+dx+hv[2]*gw)*zoom))
                        crop = img_data[max(0, ay0):min(h, ay1), max(0, ax0):min(w, ax1)]
                        if crop.size > 0: total_intensity += np.mean(crop); count += 1
                if count > 0 and total_intensity / count < min_intensity: min_intensity = total_intensity / count; best_dx, best_dy = dx, dy
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

    def wipe_content(self, image: Image.Image, spans: List[Dict[str, Any]], image_masks: List[Dict[str, Any]], zoom: float, bg_color=(255, 255, 255)) -> Tuple[Image.Image, np.ndarray, Dict[str, float]]:
        img_data = np.array(image.convert("RGB"))
        h, w, _ = img_data.shape
        mask = np.zeros((h, w), dtype=bool)
        dx, dy = self.find_optimal_offsets(img_data, spans, zoom)
        
        # 1. Wipe Text
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
                    # Use 1px padding for text wiping
                    y0, y1, x0, x1 = max(0, iy0-1), min(h, iy1+2), max(0, ix0-1), min(w, ix1+2)
                    img_data[y0:y1, x0:x1] = bg_color; mask[y0:y1, x0:x1] = True
        
        # 2. Wipe Images (Pixel-Aware)
        from scipy.ndimage import binary_dilation
        for im_data in image_masks:
            ibox, imask = im_data["bbox"], im_data["mask"]
            ix0, iy0, ix1, iy1 = [int(round(c)) for c in ibox]
            # Resize mask to fit zoomed bbox
            mask_img = Image.fromarray(imask).resize((max(1, ix1-ix0), max(1, iy1-iy0)), Image.NEAREST)
            m_arr = np.array(mask_img)
            
            # Apply mask to wipe
            target_region = img_data[iy0:iy1, ix0:ix1]
            if target_region.shape[:2] == m_arr.shape:
                # Dilation to ensure clean edges
                m_arr = binary_dilation(m_arr, structure=np.ones((3, 3)))
                target_region[m_arr] = bg_color
                mask[iy0:iy1, ix0:ix1][m_arr] = True
                
        return Image.fromarray(img_data), mask, {"dx": dx, "dy": dy}

    def detect_artifacts(self, original: Image.Image, wiped: Image.Image, bg_color: Tuple[int, int, int]) -> List[Tuple[int, int, int, int]]:
        from scipy.ndimage import label, binary_dilation, binary_erosion
        w_data = np.array(wiped.convert("RGB")).astype(float)
        diff = np.abs(w_data - np.full_like(w_data, bg_color))
        mask = np.any(diff > 30, axis=2)
        if mask.ndim != 2: return []
        h_line = binary_dilation(binary_erosion(mask, structure=np.ones((1, 15))), structure=np.ones((1, 15)))
        v_line = binary_dilation(binary_erosion(mask, structure=np.ones((15, 1))), structure=np.ones((15, 1)))
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

    def join_tokens(self, char_bboxes: List[List[float]], glyph_bboxes: List[List[float]], image_bboxes: List[List[float]], artifact_bboxes: List[Tuple[int, int, int, int]]) -> List[Dict[str, Any]]:
        """
        Tokenization: Merges characters into words using glyph bboxes for proximity.
        Visual components (images, artifacts) are merged if nearby, but separators are kept individual.
        """
        from .line_detector import is_separator
        
        # 1. Merge characters into words using GLYPH bboxes for proximity
        # but outputting the merged ACTUAL bboxes.
        word_tokens = self._merge_chars_to_words(char_bboxes, glyph_bboxes)
        
        # 2. Prepare initial visual components
        vis_comps = []
        for b in image_bboxes: vis_comps.append({"type": "image", "bbox": list(b)})
        for b in artifact_bboxes: vis_comps.append({"type": "artifact", "bbox": list(b)})

        # 3. Identify Separator Lines (Exclude from merging)
        separators = []
        mergeable_vis = []
        for v in vis_comps:
            if is_separator(v["bbox"]):
                separators.append(v)
            else:
                mergeable_vis.append(v)

        # 4. Iteratively merge 'mergeable_vis' visual components
        merged = True
        while merged:
            merged = False
            for i in range(len(mergeable_vis)):
                for j in range(i + 1, len(mergeable_vis)):
                    if self._is_nearby(mergeable_vis[i]["bbox"], mergeable_vis[j]["bbox"], threshold=15):
                        mergeable_vis[i]["bbox"] = [
                            min(mergeable_vis[i]["bbox"][0], mergeable_vis[j]["bbox"][0]),
                            min(mergeable_vis[i]["bbox"][1], mergeable_vis[j]["bbox"][1]),
                            max(mergeable_vis[i]["bbox"][2], mergeable_vis[j]["bbox"][2]),
                            max(mergeable_vis[i]["bbox"][3], mergeable_vis[j]["bbox"][3])
                        ]
                        mergeable_vis.pop(j)
                        merged = True
                        break
                if merged: break

        # 5. Combine and assign IDs
        tokens = []
        v_idx, s_idx, t_idx = 1, 1, 1
        
        # Add Separators (S)
        for s in separators:
            tokens.append({"type": "visual", "subtype": "separator", "bbox": s["bbox"], "id": f"S{s_idx}"})
            s_idx += 1
            
        # Add Merged Visual Blocks (V)
        for mv in mergeable_vis:
            tokens.append({"type": "visual", "subtype": "block", "bbox": mv["bbox"], "id": f"V{v_idx}"})
            v_idx += 1
        
        # Add Words (T)
        for w in word_tokens:
            tokens.append({"type": "text", "bbox": w, "id": f"T{t_idx}"})
            t_idx += 1
        
        return tokens

    def _merge_chars_to_words(self, actual_bboxes: List[List[float]], glyph_bboxes: List[List[float]]) -> List[List[float]]:
        if not actual_bboxes: return []
        
        # Pair actual and glyph bboxes
        pairs = []
        for a, g in zip(actual_bboxes, glyph_bboxes):
            pairs.append({"actual": list(a), "glyph": list(g)})
            
        # Sort by glyph y0 then x0
        pairs = sorted(pairs, key=lambda p: (p["glyph"][1], p["glyph"][0]))
        
        # Group into lines based on glyph vertical overlap
        lines = []
        if pairs:
            curr_line = [pairs[0]]
            for i in range(1, len(pairs)):
                prev, curr = curr_line[-1]["glyph"], pairs[i]["glyph"]
                overlap = min(prev[3], curr[3]) - max(prev[1], curr[1])
                h = min(prev[3] - prev[1], curr[3] - curr[1])
                if overlap > h * 0.6: # Stricter vertical overlap for lines
                    curr_line.append(pairs[i])
                else:
                    lines.append(sorted(curr_line, key=lambda p: p["glyph"][0]))
                    curr_line = [pairs[i]]
            lines.append(sorted(curr_line, key=lambda p: p["glyph"][0]))
            
        # Group lines into words based on glyph horizontal proximity
        words = []
        for line in lines:
            if not line: continue
            curr_word_actual = line[0]["actual"]
            curr_word_glyph = line[0]["glyph"]
            
            for i in range(1, len(line)):
                prev_g = line[i-1]["glyph"]
                curr_g = line[i]["glyph"]
                curr_a = line[i]["actual"]
                
                # Use glyph bboxes to check horizontal "touching"
                # In many fonts, glyph bboxes for adjacent characters touch or slightly overlap
                gap = curr_g[0] - prev_g[2]
                
                # Threshold for horizontal word grouping (e.g. 2px)
                if gap < 3:
                    curr_word_actual = [
                        min(curr_word_actual[0], curr_a[0]), min(curr_word_actual[1], curr_a[1]),
                        max(curr_word_actual[2], curr_a[2]), max(curr_word_actual[3], curr_a[3])
                    ]
                    curr_word_glyph = [
                        min(curr_word_glyph[0], curr_g[0]), min(curr_word_glyph[1], curr_g[1]),
                        max(curr_word_glyph[2], curr_g[2]), max(curr_word_glyph[3], curr_g[3])
                    ]
                else:
                    words.append(curr_word_actual)
                    curr_word_actual = curr_a
                    curr_word_glyph = curr_g
            words.append(curr_word_actual)
            
        return words

    def _is_nearby(self, bbox1: List[float], bbox2: List[float], threshold: float) -> bool:
        return not (bbox1[2] < bbox2[0] - threshold or
                    bbox1[0] > bbox2[2] + threshold or
                    bbox1[3] < bbox2[1] - threshold or
                    bbox1[1] > bbox2[3] + threshold)
