import re
import json
from typing import List, Dict, Any, Tuple
from tool.READ.logic.pdf.formatter import get_span_style, strip_non_standard_chars, is_sentence_complete, format_segments_with_color_merging

class SemanticsEngine:
    """
    Handles semantic tagging, logical block merging, and final output generation.
    Incorporates layout analysis (gutter detection) for column-aware processing.
    """
    def __init__(self, page_rect: Any, median_size: float):
        self.page_rect = page_rect
        self.page_width = page_rect.width
        self.page_height = page_rect.height
        self.median_size = median_size

    def process(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 1. Layout Analysis: Group spans into blocks based on columns and lines
        blocks = self._segment_into_blocks(spans)
        
        # 2. Semantic Tagging & Segment Extraction
        semantic_items = []
        in_ref = False
        for b in blocks:
            b_type = self.identify_block_type(b)
            if b_type == "reference": in_ref = True
            elif in_ref and b_type not in ["heading", "title", "footer", "header"]: b_type = "reference"
            
            segments = []
            for line in b["lines"]:
                if not line["spans"]: continue
                line_y = line["spans"][0]["origin"][1]
                for span in line["spans"]:
                    style = get_span_style(span, self.median_size, line_y)
                    text = strip_non_standard_chars(span["text"])
                    if not text: continue
                    if not segments or segments[-1][1] != style: segments.append([text, style])
                    else: segments[-1][0] += text
            
            if not segments: continue
            semantic_items.append({
                "type": b_type, "bbox": list(b["bbox"]), "segments": segments, 
                "text": "".join([s[0] for s in segments]).strip(), "lines": b["lines"]
            })
            
        # 3. Logical Merging
        merged = []
        for item in semantic_items:
            if not merged: merged.append(item); continue
            prev = merged[-1]
            if prev["type"] == item["type"] and (item["type"] == "reference" or (prev["type"] == "paragraph" and not is_sentence_complete(prev["text"]))):
                if prev["segments"][-1][1] == item["segments"][0][1]:
                    prev["segments"][-1][0] += item["segments"][0][0]
                    prev["segments"].extend(item["segments"][1:])
                else: prev["segments"].extend(item["segments"])
                prev["text"] = (prev["text"] + " " + item["text"]).strip()
                prev["lines"].extend(item["lines"])
                prev["bbox"] = [
                    min(prev["bbox"][0], item["bbox"][0]), min(prev["bbox"][1], item["bbox"][1]), 
                    max(prev["bbox"][2], item["bbox"][2]), max(prev["bbox"][3], item["bbox"][3])
                ]
            else: merged.append(item)
            
        # 4. Final Formatting & Splitting
        final = []
        for item in merged:
            if item["type"] == "reference": final.extend(self._split_references(item))
            else: final.append(self._format_item(item))
        return final

    def identify_block_type(self, block: Dict[str, Any]) -> str:
        bbox = block["bbox"]
        text = "".join([s["text"] for line in block["lines"] for s in line["spans"]]).strip()
        
        if block.get("is_image"): return "image"
        
        # Margin-based header/footer detection
        margin = self.page_height * 0.05
        if bbox[3] < margin: return "header"
        if bbox[1] > self.page_height - margin: return "footer"
        
        max_size = 0
        for line in block["lines"]:
            for span in line["spans"]: max_size = max(max_size, span["size"])
                
        if max_size > self.median_size * 1.5:
            page_mid = self.page_width / 2
            block_mid = (bbox[0] + bbox[2]) / 2
            if abs(block_mid - page_mid) < self.page_width * 0.1: return "title"
            return "heading"
        
        if max_size > self.median_size * 1.1: return "heading"
        if re.match(r'^(?:\[\d+\]|\d+\.)', text) or text.lower() == "references": return "reference"
        return "paragraph"

    def _segment_into_blocks(self, spans: List[Dict[str, Any]], depth: int = 0) -> List[Dict[str, Any]]:
        if not spans: return []
        if depth > 5: return self._cluster_into_blocks(spans)

        # 1. Filter body spans (excluding obvious header/footer)
        header_y = self.page_height * 0.05
        footer_y = self.page_height * 0.95
        
        header_s, footer_s, body_s = [], [], []
        for s in spans:
            mid_y = (s['bbox'][1] + s['bbox'][3]) / 2
            if mid_y < header_y: header_s.append(s)
            elif mid_y > footer_y: footer_s.append(s)
            else: body_s.append(s)
            
        header_blocks = self._cluster_into_blocks(header_s) if header_s else []
        footer_blocks = self._cluster_into_blocks(footer_s) if footer_s else []
        
        if not body_s: return header_blocks + footer_blocks

        # 2. Check for Vertical Gutter (Columns)
        x_min = min(s['bbox'][0] for s in body_s)
        x_max = max(s['bbox'][2] for s in body_s)
        mid_x = (x_min + x_max) / 2
        gutters = self._find_gutters(body_s, x_min, x_max)
        
        best_gutter = None
        for g0, g1 in sorted(gutters, key=lambda g: g[1] - g[0], reverse=True):
            if abs((g0 + g1) / 2 - mid_x) < (x_max - x_min) * 0.15:
                best_gutter = (g0, g1); break
        
        if best_gutter:
            g_mid = (best_gutter[0] + best_gutter[1]) / 2
            left_s = [s for s in body_s if s['bbox'][2] <= g_mid]
            right_s = [s for s in body_s if s['bbox'][0] >= g_mid]
            if left_s and right_s:
                return header_blocks + self._segment_into_blocks(left_s, depth + 1) + self._segment_into_blocks(right_s, depth + 1) + footer_blocks

        # 3. Split into lines and zones
        lines = self._group_into_lines(body_s)
        zones, curr_multi = [], []
        for line in lines:
            lx0, lx1 = min(s['bbox'][0] for s in line), max(s['bbox'][2] for s in line)
            is_spanning = (lx1 - lx0) > (x_max - x_min) * 0.75
            if is_spanning:
                if curr_multi: zones.append(curr_multi); curr_multi = []
                zones.append(line)
            else: curr_multi.extend(line)
        if curr_multi: zones.append(curr_multi)
        
        final_blocks = []
        for zone in zones: final_blocks.extend(self._cluster_into_blocks(zone))
        return header_blocks + final_blocks + footer_blocks

    def _find_gutters(self, spans: List[Dict[str, Any]], x_min: float, x_max: float) -> List[Tuple[float, float]]:
        width = int(x_max - x_min) + 1
        occ = [0] * width
        for s in spans:
            for x in range(int(s['bbox'][0] - x_min), int(s['bbox'][2] - x_min) + 1):
                if 0 <= x < width: occ[x] = 1
        gutters, start = [], None
        for x in range(width):
            if occ[x] == 0:
                if start is None: start = x
            elif start is not None:
                if (x - start) > 5: gutters.append((start + x_min, x + x_min))
                start = None
        return gutters

    def _group_into_lines(self, spans: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not spans: return []
        spans.sort(key=lambda s: (s['bbox'][1], s['bbox'][0]))
        lines, curr_line = [], [spans[0]]
        for i in range(1, len(spans)):
            prev, curr = curr_line[-1], spans[i]
            overlap = min(prev['bbox'][3], curr['bbox'][3]) - max(prev['bbox'][1], curr['bbox'][1])
            if overlap > (min(prev['bbox'][3]-prev['bbox'][1], curr['bbox'][3]-curr['bbox'][1]) * 0.4): curr_line.append(curr)
            else: lines.append(sorted(curr_line, key=lambda s: s['bbox'][0])); curr_line = [curr]
        lines.append(sorted(curr_line, key=lambda s: s['bbox'][0]))
        return sorted(lines, key=lambda l: min(s['bbox'][1] for s in l))

    def _cluster_into_blocks(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        lines = self._group_into_lines(spans)
        if not lines: return []
        blocks, curr_b = [], [lines[0]]
        for i in range(1, len(lines)):
            prev_y1, curr_y0 = max(s['bbox'][3] for s in lines[i-1]), min(s['bbox'][1] for s in lines[i])
            if (curr_y0 - prev_y1) > self.median_size * 0.7:
                blocks.append(self._create_block(curr_b)); curr_b = [lines[i]]
            else: curr_b.append(lines[i])
        blocks.append(self._create_block(curr_b))
        return blocks

    def _create_block(self, lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_s = [s for l in lines for s in l]
        bbox = [min(s['bbox'][0] for s in all_s), min(s['bbox'][1] for s in all_s), max(s['bbox'][2] for s in all_s), max(s['bbox'][3] for s in all_s)]
        return {"bbox": bbox, "lines": [{"spans": l} for l in lines]}

    def _split_references(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        entries, current = [], []
        for line in item["lines"]:
            text = "".join([s["text"] for s in line["spans"]]).strip()
            if re.match(r'^(?:\[\d+\]|\d+\.)', text) or text.lower() == "references":
                if current: entries.append(self._create_ref(current))
                current = [line]
            else:
                if not current: current = [line]
                else: current.append(line)
        if current: entries.append(self._create_ref(current))
        return [self._format_item(e) for e in entries]

    def _create_ref(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        all_s = [s for l in lines for s in l["spans"]]
        bbox = [min(s['bbox'][0] for s in all_s), min(s['bbox'][1] for s in all_s), max(s['bbox'][2] for s in all_s), max(s['bbox'][3] for s in all_s)]
        segments = []
        for l in lines:
            line_y = l["spans"][0]["origin"][1] if l["spans"] else 0
            for span in l["spans"]:
                style = get_span_style(span, self.median_size, line_y)
                text = strip_non_standard_chars(span["text"])
                if not text: continue
                if not segments or segments[-1][1] != style: segments.append([text, style])
                else: segments[-1][0] += text
        return {"type": "reference", "bbox": bbox, "segments": segments, "text": "".join([s[0] for s in segments]).strip(), "lines": lines}

    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        segments, b_type = item["segments"], item["type"]
        if b_type in ["paragraph", "heading"] and segments and segments[0][1].get("bold"):
            bold_end = -1
            for i in range(1, len(segments)):
                if not segments[i][1].get("bold"): bold_end = i; break
            if bold_end != -1:
                bold_text = "".join([s[0] for s in segments[:bold_end]]).strip()
                if len(bold_text.split()) < 12 or re.match(r"^\d+(\.\d+)*\s", bold_text):
                    item["md_text"] = format_segments_with_color_merging(segments[:bold_end]).strip() + " \n\n " + format_segments_with_color_merging(segments[bold_end:]).lstrip()
                else: item["md_text"] = format_segments_with_color_merging(segments)
            else: item["md_text"] = format_segments_with_color_merging(segments)
        elif b_type == "reference":
            item["md_text"] = re.sub(r"(?i)(References)", r"**\1**", format_segments_with_color_merging(segments), count=1)
        else: item["md_text"] = format_segments_with_color_merging(segments)
        item["md_text"] = re.sub(r' +', ' ', item["md_text"]).strip()
        return item
