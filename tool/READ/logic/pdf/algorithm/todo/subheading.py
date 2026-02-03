import re
from typing import List, Dict, Any, Tuple

class SubheadingIdentifier:
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size

    def identify(self, lines: List[List[Dict[str, Any]]], preference: str = "default") -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        subheading_blocks = []
        remaining_lines = []
        
        for line in lines:
            line_text = "".join([t["text"] for t in line]).strip()
            line_bbox = [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                         max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
            
            # Subheadings are spanning and bold or have numbering
            is_spanning = (line_bbox[2] - line_bbox[0]) > self.page_width * 0.5
            if is_spanning and self._is_subheading_pattern(line_text, line):
                subheading_blocks.append(self._create_block([line]))
            else:
                remaining_lines.append(line)
        return subheading_blocks, remaining_lines

    def _is_subheading_pattern(self, text: str, line: List[Dict[str, Any]]) -> bool:
        is_bold = all(("bold" in t["font"].lower() or t["flags"] & 16) for t in line if t["text"].strip())
        max_size = max(t["size"] for t in line)
        if (re.match(r"^\d+(\.\d+)*\s+[A-Z]", text) or 
            (is_bold and max_size > self.median_size * 1.05 and (text.isupper() or re.match(r"^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$", text)))):
            return len(text.split()) < 12
        return False

    def _create_block(self, lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        import copy
        return {
            "type": "subheading",
            "bbox": bbox,
            "lines": [{"spans": copy.deepcopy(l), "bbox": bbox} for l in lines],
            "text": "".join([t["text"] for l in lines for t in l]).strip()
        }

