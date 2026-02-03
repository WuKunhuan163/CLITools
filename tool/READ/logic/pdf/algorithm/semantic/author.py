import re
import copy
from typing import List, Dict, Any, Tuple
from tool.READ.logic.pdf.formatter import get_span_style

class AuthorIdentifier:
    """
    Identifies author blocks in academic papers.
    Typically located below the title and above the abstract.
    """
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size

    def identify(self, lines: List[List[Dict[str, Any]]], preference: str = "default") -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        author_blocks = []
        remaining_lines = []
        
        for line in lines:
            line_text = "".join([t["text"] for t in line]).strip()
            line_bbox = [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                         max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
            
            # Author lines are typically in the top half
            if line_bbox[1] < self.page_height * 0.5 and self._is_author_pattern(line_text):
                author_blocks.append(self._create_block([line]))
            else:
                remaining_lines.append(line)
        return author_blocks, remaining_lines

    def _is_author_pattern(self, text: str) -> bool:
        text = text.strip()
        words = text.split()
        if len(words) < 2 or len(words) > 100: return False
        
        # Patterns: "By ", commas, "and", initials
        comma_count = text.count(",")
        and_count = text.lower().count(" and ")
        initial_count = len(re.findall(r"\b[A-Z]\.", text))
        
        if text.startswith("By ") or (comma_count >= 2) or (and_count >= 1) or (initial_count >= 2):
            # Check for common non-author words to avoid false positives
            if any(x in text.lower() for x in ["abstract", "figure", "table", "introduction"]):
                return False
            return True
        return False

    def _create_block(self, lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        
        formatted_lines = [{"spans": copy.deepcopy(l), "bbox": bbox} for l in lines]
        
        # Create segments for formatting
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
