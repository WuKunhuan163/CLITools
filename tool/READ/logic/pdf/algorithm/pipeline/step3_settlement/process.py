import re
from typing import List, Dict, Any
from tool.READ.logic.pdf.formatter import format_segments_with_color_merging, get_span_style, strip_non_standard_chars

class Settlement:
    """
    Final phase: handles formatting refinement, reference splitting, and output generation.
    """
    def __init__(self, median_size: float):
        self.median_size = median_size

    def settle(self, merged_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        settled = []
        for item in merged_items:
            if item["type"] == "reference":
                # Splitting logic for references
                entries = self._split_references(item)
                for entry in entries:
                    settled.append(self._format_item(entry))
            else:
                settled.append(self._format_item(item))
        return settled

    def _split_references(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        entries = []
        current_ref_lines = []
        for line in item["lines"]:
            line_text = "".join([s["text"] for s in line["spans"]]).strip()
            if re.match(r'^(?:\[\d+\]|\d+\.)', line_text) or line_text.lower() == "references":
                if current_ref_lines:
                    entries.append(self._create_ref_item(current_ref_lines))
                current_ref_lines = [line]
            else:
                if not current_ref_lines: current_ref_lines = [line]
                else: current_ref_lines.append(line)
        
        if current_ref_lines:
            entries.append(self._create_ref_item(current_ref_lines))
        return entries

    def _create_ref_item(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l.get("spans", [])]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        
        segments = []
        for l in lines:
            line_y = l["spans"][0]["origin"][1] if l["spans"] else 0
            for span in l["spans"]:
                style = get_span_style(span, self.median_size, line_y)
                text = strip_non_standard_chars(span["text"])
                if not text: continue
                if not segments: segments.append([text, style])
                else:
                    if style == segments[-1][1]: segments[-1][0] += text
                    else: segments.append([text, style])
        
        return {
            "type": "reference",
            "bbox": bbox,
            "segments": segments,
            "text": "".join([s[0] for s in segments]).strip(),
            "lines": lines
        }

    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        segments = item["segments"]
        block_type = item["type"]
        
        block_md = ""
        if block_type in ["paragraph", "heading"]:
            if segments and segments[0][1].get("bold"):
                bold_end_idx = -1
                for i in range(1, len(segments)):
                    if not segments[i][1].get("bold"):
                        bold_end_idx = i; break
                if bold_end_idx != -1:
                    bold_text = "".join([s[0] for s in segments[:bold_end_idx]]).strip()
                    if len(bold_text.split()) < 12 or re.match(r"^\d+(\.\d+)*\s", bold_text):
                        heading_md = format_segments_with_color_merging(segments[:bold_end_idx]).strip()
                        body_md = format_segments_with_color_merging(segments[bold_end_idx:]).lstrip()
                        block_md = heading_md + " \n\n " + body_md
                    else: block_md = format_segments_with_color_merging(segments)
                else:
                    block_md = format_segments_with_color_merging(segments)
            else:
                block_md = format_segments_with_color_merging(segments)
        elif block_type == "reference":
            block_md = format_segments_with_color_merging(segments)
            block_md = re.sub(r"(?i)(References)", r"**\1**", block_md, count=1)
        else:
            block_md = format_segments_with_color_merging(segments)
            
        block_md = re.sub(r' +', ' ', block_md).strip()
        item["md_text"] = block_md
        return item
