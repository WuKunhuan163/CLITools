from typing import List, Dict, Any, Tuple
import re
import copy
from .utils import create_settled_block

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
            # Skip separator lines
            if len(line) == 1 and line[0].get("type") == "separator":
                remaining_lines.append(line)
                i += 1
                continue

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
                
                title_blocks.append(create_settled_block(title_lines, "title", self.median_size))
                i = j
                continue
            
            remaining_lines.append(line)
            i += 1
            
        return title_blocks, remaining_lines

    def _get_line_bbox(self, line: List[Dict[str, Any]]) -> List[float]:
        return [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
