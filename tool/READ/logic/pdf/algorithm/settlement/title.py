from typing import List, Dict, Any, Tuple
import re
import copy
from tool.READ.logic.pdf.formatter import get_span_style

class TitleIdentifier:
    """
    Identifies titles in a PDF page based on font size, position, and alignment.
    """
    
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size

    def identify(self, lines: List[List[Dict[str, Any]]], preference: str = "default") -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        """
        Identifies title blocks and returns (identified_blocks, remaining_lines).
        """
        title_blocks = []
        remaining_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_bbox = self._get_line_bbox(line)
            max_font = max(t["size"] for t in line)
            
            is_large = max_font > self.median_size * 1.5
            is_at_top = line_bbox[1] < self.page_height * 0.4
            
            if is_large and is_at_top:
                title_lines = [line]
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    next_max_font = max(t["size"] for t in next_line)
                    if next_max_font > self.median_size * 1.3:
                        title_lines.append(next_line)
                        j += 1
                    else:
                        break
                
                title_blocks.append(self._create_block(title_lines))
                i = j
                continue
            
            remaining_lines.append(line)
            i += 1
            
        return title_blocks, remaining_lines

    def _get_line_bbox(self, line: List[Dict[str, Any]]) -> List[float]:
        return [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]

    def _create_block(self, lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        
        formatted_lines = [{"spans": copy.deepcopy(l), "bbox": self._get_line_bbox(l)} for l in lines]
        
        # Create segments for formatting using get_span_style
        segments = []
        for line in lines:
            line_y = line[0]["origin"][1] if line else 0
            for span in line:
                style = get_span_style(span, self.median_size, line_y)
                text = span["text"]
                if not segments:
                    segments.append([text, style])
                else:
                    if segments[-1][1] == style:
                        segments[-1][0] += text
                    else:
                        segments.append([text, style])
            # Add space between lines
            if segments and not segments[-1][0].endswith(" "):
                segments[-1][0] += " "

        return {
            "type": "title",
            "bbox": bbox,
            "lines": formatted_lines,
            "segments": segments,
            "text": " ".join(["".join([t["text"] for t in l]).strip() for l in lines])
        }
