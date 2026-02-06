import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from PIL import Image, ImageDraw

class LayoutAnalyzer:
    def __init__(self, median_size: float):
        self.median_size = median_size
        self.separators = []
        self.zones = []
        self.line_tokens = []
        self.content_tokens = []
        self.all_tokens = []

    def analyze(self, tokens: List[Dict[str, Any]], page_width: float, page_height: float) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Main entry point for layout analysis using Recursive Slicing.
        Returns (separators, ordered_tokens).
        """
        self.all_tokens = tokens
        self.line_tokens = [t for t in tokens if t.get("subtype") == "line" or t.get("subtype") == "rect"]
        self.content_tokens = [t for t in tokens if t not in self.line_tokens and not t.get("is_absorbed")]
        self.separators = []
        self.zones = []

        bbox = [0.0, 0.0, page_width, page_height]
        self._slice_recursive(tokens, bbox)
        
        ordered_tokens = self._get_reading_order(tokens, bbox)
        
        # Format separators for final output
        final_separators = []
        for i, s in enumerate(self.separators):
            final_separators.append({
                "type": "separator",
                "subtype": s["type"],
                "id": f"S{i+1}",
                "bbox": s["bbox"],
                "order_changing": s["order_changing"],
                "via_line": s.get("via_line", False)
            })
            
        return final_separators, ordered_tokens

    def _slice_recursive(self, tokens: List[Dict[str, Any]], bbox: List[float], depth: int = 0):
        if not tokens or depth > 50:
            return

        x0, y0, x1, y1 = bbox
        curr_content = [t for t in tokens if t in self.content_tokens]
        curr_lines = [t for t in tokens if t in self.line_tokens]
        
        if not curr_content:
            return

        text_tokens = [t for t in curr_content if t["type"] == "text"]
        if text_tokens:
            heights = [t.get("glyph_bbox", t["bbox"])[3] - t.get("glyph_bbox", t["bbox"])[1] for t in text_tokens]
            median_h = np.median(heights)
        else:
            median_h = self.median_size
            
        v_gap_threshold = median_h * 0.5
        h_gap_threshold = median_h * 0.2
        
        best_line_cut = self._find_line_heuristic(curr_lines, curr_content, bbox)
        
        cut_type = None
        if best_line_cut:
            cut_type = best_line_cut["type"]
        else:
            best_v_gap = self._find_best_gap(curr_content, bbox, "vertical", threshold=v_gap_threshold)
            best_h_gap = self._find_best_gap(curr_content, bbox, "horizontal", threshold=h_gap_threshold)
            
            # Prioritize vertical (columns) in T-B layout
            if best_v_gap: cut_type = "vertical"
            elif best_h_gap: cut_type = "horizontal"
        
        if not cut_type:
            return

        # Find parallel gaps
        if best_line_cut:
            all_gaps = [best_line_cut["gap"]]
        else:
            all_gaps = self._find_all_gaps(curr_content, bbox, cut_type, 
                                           threshold=(v_gap_threshold if cut_type == "vertical" else h_gap_threshold))
        
        if not all_gaps: return
        all_gaps.sort()
        
        sub_bboxes = []
        curr_bound = x0 if cut_type == "vertical" else y0
        
        for gap_start, gap_end in all_gaps:
            mid = (gap_start + gap_end) / 2
            
            # Order-changing detection
            natural_order = self._get_natural_order(curr_content, median_h)
            
            if cut_type == "vertical":
                left_tokens = [t for t in tokens if t.get("glyph_bbox", t["bbox"])[2] <= gap_start]
                right_tokens = [t for t in tokens if t.get("glyph_bbox", t["bbox"])[0] >= gap_end]
                split_order = self._get_natural_order([t for t in left_tokens if t in self.content_tokens], median_h) + \
                              self._get_natural_order([t for t in right_tokens if t in self.content_tokens], median_h)
                order_changing = [t["id"] for t in natural_order] != [t["id"] for t in split_order]
                
                self.separators.append({
                    "type": "vertical", "bbox": [mid, y0, mid, y1],
                    "order_changing": order_changing, "depth": depth, "width": gap_end - gap_start,
                    "via_line": True if best_line_cut else False
                })
                self.zones.append({"bbox": [gap_start, y0, gap_end, y1], "type": "v_zone"})
                sub_bboxes.append([curr_bound, y0, gap_start, y1])
                curr_bound = gap_end
            else:
                top_tokens = [t for t in tokens if t.get("glyph_bbox", t["bbox"])[3] <= gap_start]
                bottom_tokens = [t for t in tokens if t.get("glyph_bbox", t["bbox"])[1] >= gap_end]
                split_order = self._get_natural_order([t for t in top_tokens if t in self.content_tokens], median_h) + \
                              self._get_natural_order([t for t in bottom_tokens if t in self.content_tokens], median_h)
                order_changing = [t["id"] for t in natural_order] != [t["id"] for t in split_order]

                self.separators.append({
                    "type": "horizontal", "bbox": [x0, mid, x1, mid],
                    "order_changing": order_changing, "depth": depth, "height": gap_end - gap_start,
                    "via_line": True if best_line_cut else False
                })
                self.zones.append({"bbox": [x0, gap_start, x1, gap_end], "type": "h_zone"})
                sub_bboxes.append([x0, curr_bound, x1, gap_start])
                curr_bound = gap_end
        
        if cut_type == "vertical": sub_bboxes.append([curr_bound, y0, x1, y1])
        else: sub_bboxes.append([x0, curr_bound, x1, y1])
        
        for sb in sub_bboxes:
            sb_tokens = [t for t in tokens if t.get("glyph_bbox", t["bbox"])[0] >= sb[0] - 0.1 and t.get("glyph_bbox", t["bbox"])[2] <= sb[2] + 0.1 and \
                                             t.get("glyph_bbox", t["bbox"])[1] >= sb[1] - 0.1 and t.get("glyph_bbox", t["bbox"])[3] <= sb[3] + 0.1]
            self._slice_recursive(sb_tokens, sb, depth + 1)

    def _get_reading_order(self, tokens: List[Dict[str, Any]], bbox: List[float]) -> List[Dict[str, Any]]:
        tokens = [t for t in tokens if t not in self.line_tokens and not t.get("is_absorbed")]
        if not tokens: return []
            
        x0, y0, x1, y1 = bbox
        text_tokens = [t for t in tokens if t["type"] == "text"]
        median_h = np.median([t.get("glyph_bbox", t["bbox"])[3] - t.get("glyph_bbox", t["bbox"])[1] for t in text_tokens]) if text_tokens else self.median_size
            
        curr_lines = [t for t in self.line_tokens if t.get("glyph_bbox", t["bbox"])[0] >= x0 - 0.1 and t.get("glyph_bbox", t["bbox"])[2] <= x1 + 0.1 and \
                                                  t.get("glyph_bbox", t["bbox"])[1] >= y0 - 0.1 and t.get("glyph_bbox", t["bbox"])[3] <= y1 + 0.1]
        best_line_cut = self._find_line_heuristic(curr_lines, tokens, bbox)
        
        cut_type = None
        if best_line_cut:
            cut_type = best_line_cut["type"]
            best_gap = best_line_cut["gap"]
        else:
            v_gap = self._find_best_gap(tokens, bbox, "vertical", threshold=median_h * 0.5)
            h_gap = self._find_best_gap(tokens, bbox, "horizontal", threshold=median_h * 0.2)
            if v_gap:
                cut_type, best_gap = "vertical", v_gap
            elif h_gap:
                cut_type, best_gap = "horizontal", h_gap
            
        if cut_type:
            # For reading order, we process parallel gaps in order
            all_gaps = self._find_all_gaps(tokens, bbox, cut_type, threshold=(median_h * 0.5 if cut_type == "vertical" else median_h * 0.2))
            if not all_gaps: return self._get_natural_order(tokens, median_h)
            all_gaps.sort()
            
            result_order = []
            curr_bound = x0 if cut_type == "vertical" else y0
            for gap_start, gap_end in all_gaps:
                if cut_type == "vertical":
                    sb = [curr_bound, y0, gap_start, y1]
                    curr_bound = gap_end
                else:
                    sb = [x0, curr_bound, x1, gap_start]
                    curr_bound = gap_end
                
                sb_tokens = [t for t in tokens if t.get("glyph_bbox", t["bbox"])[0] >= sb[0] - 0.1 and t.get("glyph_bbox", t["bbox"])[2] <= sb[2] + 0.1 and \
                                                 t.get("glyph_bbox", t["bbox"])[1] >= sb[1] - 0.1 and t.get("glyph_bbox", t["bbox"])[3] <= sb[3] + 0.1]
                result_order.extend(self._get_reading_order(sb_tokens, sb))
            
            # Last block
            if cut_type == "vertical": sb = [curr_bound, y0, x1, y1]
            else: sb = [x0, curr_bound, x1, y1]
            sb_tokens = [t for t in tokens if t.get("glyph_bbox", t["bbox"])[0] >= sb[0] - 0.1 and t.get("glyph_bbox", t["bbox"])[2] <= sb[2] + 0.1 and \
                                             t.get("glyph_bbox", t["bbox"])[1] >= sb[1] - 0.1 and t.get("glyph_bbox", t["bbox"])[3] <= sb[3] + 0.1]
            result_order.extend(self._get_reading_order(sb_tokens, sb))
            return result_order
        else:
            return self._get_natural_order(tokens, median_h)

    def _get_natural_order(self, tokens: List[Dict[str, Any]], median_h: float) -> List[Dict[str, Any]]:
        if not tokens: return []
        vertical_tolerance = median_h * 0.5
        sorted_tokens = sorted(tokens, key=lambda t: (t.get("glyph_bbox", t["bbox"])[1], t.get("glyph_bbox", t["bbox"])[0]))
        final_sorted = []
        while sorted_tokens:
            curr = sorted_tokens.pop(0)
            line = [curr]
            curr_y = curr.get("glyph_bbox", curr["bbox"])[1]
            i = 0
            while i < len(sorted_tokens):
                t = sorted_tokens[i]
                if abs(t.get("glyph_bbox", t["bbox"])[1] - curr_y) < vertical_tolerance:
                    line.append(sorted_tokens.pop(i))
                else: i += 1
            line.sort(key=lambda t: t.get("glyph_bbox", t["bbox"])[0])
            final_sorted.extend(line)
        return final_sorted

    def _find_best_gap(self, tokens: List[Dict[str, Any]], bbox: List[float], orientation: str, threshold: float) -> Optional[Tuple[float, float]]:
        gaps = self._find_all_gaps(tokens, bbox, orientation, threshold)
        if not gaps: return None
        return max(gaps, key=lambda g: g[1] - g[0])

    def _find_all_gaps(self, tokens: List[Dict[str, Any]], bbox: List[float], orientation: str, threshold: float) -> List[Tuple[float, float]]:
        x0, y0, x1, y1 = bbox
        intervals = []
        for t in tokens:
            tb = t.get("glyph_bbox", t["bbox"])
            if orientation == "vertical":
                if tb[3] > y0 + 1 and tb[1] < y1 - 1: intervals.append((max(x0, tb[0]), min(x1, tb[2])))
            else:
                if tb[2] > x0 + 1 and tb[0] < x1 - 1: intervals.append((max(y0, tb[1]), min(y1, tb[3])))
        if not intervals: return []
        intervals.sort()
        merged = []
        if intervals:
            curr_start, curr_end = intervals[0]
            for next_start, next_end in intervals[1:]:
                if next_start < curr_end: curr_end = max(curr_end, next_end)
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
        gaps = []
        for i in range(len(merged) - 1):
            gap_start, gap_end = merged[i][1], merged[i+1][0]
            if gap_end - gap_start > threshold:
                gaps.append((gap_start, gap_end))
        return gaps

    def _find_line_heuristic(self, curr_lines: List[Dict[str, Any]], curr_content: List[Dict[str, Any]], bbox: List[float]) -> Optional[Dict[str, Any]]:
        x0, y0, x1, y1 = bbox
        for line in curr_lines:
            lb = line.get("glyph_bbox", line["bbox"])
            if (lb[2] - lb[0]) > (lb[3] - lb[1]) * 5: # Horizontal
                if lb[0] < x0 + 10 and lb[2] > x1 - 10:
                    top_content = [t for t in curr_content if t.get("glyph_bbox", t["bbox"])[3] <= lb[1]]
                    bot_content = [t for t in curr_content if t.get("glyph_bbox", t["bbox"])[1] >= lb[3]]
                    if top_content and bot_content:
                        gap_y0 = max([t.get("glyph_bbox", t["bbox"])[3] for t in top_content])
                        gap_y1 = min([t.get("glyph_bbox", t["bbox"])[1] for t in bot_content])
                        return {"type": "horizontal", "gap": (gap_y0, gap_y1), "line_id": line["id"]}
            elif (lb[3] - lb[1]) > (lb[2] - lb[0]) * 5: # Vertical
                if lb[1] < y0 + 10 and lb[3] > y1 - 10:
                    left_content = [t for t in curr_content if t.get("glyph_bbox", t["bbox"])[2] <= lb[0]]
                    right_content = [t for t in curr_content if t.get("glyph_bbox", t["bbox"])[0] >= lb[2]]
                    if left_content and right_content:
                        gap_x0 = max([t.get("glyph_bbox", t["bbox"])[2] for t in left_content])
                        gap_x1 = min([t.get("glyph_bbox", t["bbox"])[0] for t in right_content])
                        return {"type": "vertical", "gap": (gap_x0, gap_x1), "line_id": line["id"]}
        return None

    def visualize_layout(self, separators: List[Dict[str, Any]], zones: List[Dict[str, Any]], all_tokens: List[Dict[str, Any]], output_path: Path, page_width: int, page_height: int, background_img: Image.Image = None):
        if background_img:
            img = background_img.convert("RGBA").copy()
            if img.size != (page_width, page_height):
                img = img.resize((page_width, page_height), Image.LANCZOS)
        else:
            img = Image.new("RGBA", (page_width, page_height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 1. Draw zones
        for zone in zones:
            draw.rectangle(zone["bbox"], fill=(200, 200, 200, 100))
            
        # 2. Draw separators
        for s in separators:
            bbox = s["bbox"]
            color = (255, 0, 0, 255) if s.get("order_changing") else (0, 0, 255, 255)
            # Ensure it's a line even if bbox is a rect
            if s["subtype"] == "vertical":
                mid_x = (bbox[0] + bbox[2]) / 2
                draw.line([mid_x, bbox[1], mid_x, bbox[3]], fill=color, width=3)
                draw.text((mid_x + 5, (bbox[1] + bbox[3]) / 2), s["id"], fill=color)
            else:
                mid_y = (bbox[1] + bbox[3]) / 2
                draw.line([bbox[0], mid_y, bbox[2], mid_y], fill=color, width=3)
                draw.text(((bbox[0] + bbox[2]) / 2, mid_y + 5), s["id"], fill=color)
        
        # 3. Draw Legend
        legend_h = 40
        legend_y = page_height - legend_h
        draw.rectangle([0, legend_y, page_width, page_height], fill=(240, 240, 240, 255))
        draw.rectangle([20, legend_y + 10, 50, legend_y + 30], fill=(255, 0, 0, 255))
        draw.text((60, legend_y + 12), "Order-Changing Separator", fill="black")
        draw.rectangle([250, legend_y + 10, 280, legend_y + 30], fill=(0, 0, 255, 255))
        draw.text((290, legend_y + 12), "Order-Preserving Separator", fill="black")
        
        img.save(output_path)
