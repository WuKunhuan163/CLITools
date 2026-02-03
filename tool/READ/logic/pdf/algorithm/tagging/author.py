import re
import copy
from typing import List, Dict, Any, Tuple
from tool.READ.logic.pdf.formatter import get_span_style

class AuthorIdentifier:
    """
    Tags potential author blocks.
    In "Tagging" phase, items are not settled but marked for future reference.
    """
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size

    def identify(self, lines: List[List[Dict[str, Any]]], preference: str = "default") -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        """
        Tags lines as author blocks.
        NOTE: Returns (tagged_blocks, all_lines) - Tagged blocks are NOT removed from all_lines.
        """
        tagged_blocks = []
        
        for line in lines:
            line_text = "".join([t["text"] for t in line]).strip()
            line_bbox = [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                         max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
            
            is_author, rationale = self._check_author(line_text, line_bbox)
            if is_author:
                block = self._create_block([line])
                block["rationale"] = rationale
                tagged_blocks.append(block)
                
        return tagged_blocks, lines

    def _check_author(self, text: str, bbox: List[float]) -> Tuple[bool, str]:
        text = text.strip()
        words = text.split()
        if len(words) < 2 or len(words) > 50: 
            return False, f"word_count={len(words)} out of range"
        
        # Position check: Authors are usually in top 40%
        if bbox[1] > self.page_height * 0.4:
            return False, f"position_y={bbox[1]} too low"

        # Patterns
        has_by = text.lower().startswith("by ")
        comma_count = text.count(",")
        and_count = text.lower().count(" and ")
        initial_count = len(re.findall(r"\b[A-Z]\.", text))
        
        # Avoid common false positives
        forbidden = ["abstract", "figure", "table", "introduction", "points", "3d", "render"]
        if any(x in text.lower() for x in forbidden):
            return False, f"contains_forbidden_word"

        rationale = f"by={has_by}, commas={comma_count}, and={and_count}, initials={initial_count}"
        if has_by or (comma_count >= 2) or (initial_count >= 2) or (and_count >= 1 and len(words) < 15):
            return True, rationale
            
        return False, f"no_pattern_match ({rationale})"

    def _create_block(self, lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        
        formatted_lines = [{"spans": copy.deepcopy(l), "bbox": bbox} for l in lines]
        segments = []
        for line in lines:
            line_y = line[0]["origin"][1] if line else 0
            for span in line:
                style = get_span_style(span, self.median_size, line_y)
                text = span["text"]
                if not segments: segments.append([text, style])
                else:
                    if segments[-1][1] == style: segments[-1][0] += text
                    else: segments.append([text, style])
            if segments and not segments[-1][0].endswith(" "):
                segments[-1][0] += " "

        return {
            "type": "author",
            "bbox": bbox,
            "lines": formatted_lines,
            "segments": segments,
            "text": "".join(["".join([t["text"] for t in l]) for l in lines]).strip()
        }
