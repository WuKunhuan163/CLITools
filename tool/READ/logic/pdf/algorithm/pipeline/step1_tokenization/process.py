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

    def join_tokens(self, char_bboxes: List[List[float]], glyph_bboxes: List[List[float]], image_bboxes: List[List[float]], artifact_bboxes: List[Tuple[int, int, int, int]], spans: List[Dict[str, Any]] = None, vis_img: Image.Image = None) -> List[Dict[str, Any]]:
        """
        Tokenization: Merges characters into words using glyph bboxes for proximity.
        Preserves style information (font, size, bold, italic, color).
        Identifies lines and boxes.
        """
        from .line_detector import is_separator
        
        # 1. Merge characters into words
        word_tokens = self._merge_chars_to_words(char_bboxes, glyph_bboxes, spans)
        
        # 1.5 Assign IDs to word tokens early for absorption tracking
        for i, w in enumerate(word_tokens):
            w["id"] = f"T{i+1}"
        
        # 2. Prepare initial visual components
        vis_comps = []
        for i, b in enumerate(image_bboxes): 
            vis_comps.append({"type": "image", "bbox": list(b), "comp_ids": [f"I{i+1}"]})
        for i, b in enumerate(artifact_bboxes): 
            vis_comps.append({"type": "artifact", "bbox": list(b), "comp_ids": [f"A{i+1}"]})

        # 3. Identify Lines (Exclude from merging)
        lines = []
        mergeable_vis = []
        for v in vis_comps:
            if is_separator(v["bbox"]):
                lines.append(v)
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
                        # Merge component IDs
                        mergeable_vis[i]["comp_ids"].extend(mergeable_vis[j]["comp_ids"])
                        mergeable_vis.pop(j)
                        merged = True
                        break
                if merged: break

        # 5. Identify Boxes from merged visual blocks
        final_mergeable = []
        boxes = []
        for mv in mergeable_vis:
            if self._is_box(mv["bbox"], word_tokens, vis_img):
                boxes.append(mv)
            else:
                final_mergeable.append(mv)

        # 6. Absorb nearby words into visual blocks (NOT boxes)
        # Note: We keep the text tokens in the final list so they are rendered,
        # but we expand the visual block's bbox to include them.
        consumed_text_ids = set()
        for w_data in word_tokens:
            w_bbox = w_data["bbox"]
            for fv in final_mergeable:
                if self._is_nearby(w_bbox, fv["bbox"], threshold=5):
                    fv["bbox"] = [
                        min(fv["bbox"][0], w_bbox[0]), min(fv["bbox"][1], w_bbox[1]),
                        max(fv["bbox"][2], w_bbox[2]), max(fv["bbox"][3], w_bbox[3])
                    ]
                    # Link text to visual block
                    if "absorbed_text_ids" not in fv: fv["absorbed_text_ids"] = []
                    fv["absorbed_text_ids"].append(w_data["id"])
                    consumed_text_ids.add(w_data["id"])
                    break

        # 7. Combine and assign IDs
        tokens = []
        v_idx, l_idx, b_idx = 1, 1, 1
        
        for l in lines:
            tokens.append({"type": "visual", "subtype": "line", "bbox": l["bbox"], "id": f"L{l_idx}", "comp_ids": l["comp_ids"]})
            l_idx += 1
            
        for box in boxes:
            tokens.append({"type": "visual", "subtype": "box", "bbox": box["bbox"], "id": f"B{b_idx}", "comp_ids": box["comp_ids"]})
            b_idx += 1

        for fv in final_mergeable:
            tokens.append({
                "type": "visual", "subtype": "block", "bbox": fv["bbox"], "id": f"V{v_idx}", 
                "comp_ids": fv["comp_ids"], "absorbed_text_ids": fv.get("absorbed_text_ids", [])
            })
            v_idx += 1
        
        for w in word_tokens:
            tokens.append({
                "type": "text", "bbox": w["bbox"], "glyph_bbox": w["glyph_bbox"], "id": w["id"],
                "text": w["text"], "font": w["font"], "size": w["size"],
                "color": w["color"], "flags": w["flags"],
                "is_absorbed": w["id"] in consumed_text_ids
            })
        
        return tokens

    def _is_box(self, bbox: List[float], word_tokens: List[Dict[str, Any]], vis_img: Image.Image) -> bool:
        """
        Predict if a visual component is a box.
        Criteria:
        1. High text density (text bboxes cover > 30% of box area).
        2. Uniform interior color with contrasting border (TBD).
        """
        x0, y0, x1, y1 = bbox
        box_area = (x1 - x0) * (y1 - y0)
        if box_area <= 0: return False
        
        text_area = 0
        for w in word_tokens:
            wx0, wy0, wx1, wy1 = w["bbox"]
            # Intersection
            ix0, iy0 = max(x0, wx0), max(y0, wy0)
            ix1, iy1 = min(x1, wx1), min(y1, wy1)
            if ix1 > ix0 and iy1 > iy0:
                text_area += (ix1 - ix0) * (iy1 - iy0)
        
        if text_area / box_area > 0.3:
            return True
            
        # TODO: Implement color-based box detection
        return False

    def _merge_chars_to_words(self, actual_bboxes: List[List[float]], glyph_bboxes: List[List[float]], spans: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not actual_bboxes: return []
        
        char_list = []
        if spans:
            for span in spans:
                for char_data in span.get("chars", []):
                    if char_data["c"].isspace(): continue
                    char_list.append({
                        "c": char_data["c"],
                        "font": span["font"], "size": span["size"],
                        "color": span["color"], "flags": span["flags"]
                    })
        
        pairs = []
        for i in range(len(actual_bboxes)):
            p = {"actual": list(actual_bboxes[i]), "glyph": list(glyph_bboxes[i])}
            if char_list and i < len(char_list): p.update(char_list[i])
            pairs.append(p)
            
        pairs = sorted(pairs, key=lambda p: (p["glyph"][1], p["glyph"][0]))
        
        lines = []
        if pairs:
            curr_line = [pairs[0]]
            for i in range(1, len(pairs)):
                prev, curr = curr_line[-1]["glyph"], pairs[i]["glyph"]
                overlap = min(prev[3], curr[3]) - max(prev[1], curr[1])
                h = min(prev[3] - prev[1], curr[3] - curr[1])
                if overlap > h * 0.6: curr_line.append(pairs[i])
                else: lines.append(sorted(curr_line, key=lambda p: p["glyph"][0])); curr_line = [pairs[i]]
            lines.append(sorted(curr_line, key=lambda p: p["glyph"][0]))
            
        words = []
        for line in lines:
            if not line: continue
            curr_word = {
                "text": line[0].get("c", ""), "bbox": list(line[0]["actual"]), "glyph_bbox": list(line[0]["glyph"]),
                "font": line[0].get("font", "Arial"), "size": line[0].get("size", 10),
                "color": line[0].get("color", 0), "flags": line[0].get("flags", 0)
            }
            
            for i in range(1, len(line)):
                prev_g, curr_g, curr_a, curr_c = line[i-1]["glyph"], line[i]["glyph"], line[i]["actual"], line[i].get("c", "")
                gap = curr_g[0] - prev_g[2]
                same_style = (line[i].get("font") == curr_word["font"] and line[i].get("size") == curr_word["size"])
                
                if gap < 3 and same_style:
                    curr_word["text"] += curr_c
                    curr_word["bbox"] = [min(curr_word["bbox"][0], curr_a[0]), min(curr_word["bbox"][1], curr_a[1]), max(curr_word["bbox"][2], curr_a[2]), max(curr_word["bbox"][3], curr_a[3])]
                    curr_word["glyph_bbox"] = [min(curr_word["glyph_bbox"][0], curr_g[0]), min(curr_word["glyph_bbox"][1], curr_g[1]), max(curr_word["glyph_bbox"][2], curr_g[2]), max(curr_word["glyph_bbox"][3], curr_g[3])]
                else:
                    words.append(curr_word)
                    curr_word = {"text": curr_c, "bbox": list(curr_a), "glyph_bbox": list(curr_g), "font": line[i].get("font", "Arial"), "size": line[i].get("size", 10), "color": line[i].get("color", 0), "flags": line[i].get("flags", 0)}
            words.append(curr_word)
        return words

    def _is_nearby(self, bbox1: List[float], bbox2: List[float], threshold: float) -> bool:
        return not (bbox1[2] < bbox2[0] - threshold or
                    bbox1[0] > bbox2[2] + threshold or
                    bbox1[3] < bbox2[1] - threshold or
                    bbox1[1] > bbox2[3] + threshold)
