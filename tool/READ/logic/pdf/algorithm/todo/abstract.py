import re
from typing import List, Dict, Any, Tuple

class AbstractIdentifier:
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size

    def identify(self, lines: List[List[Dict[str, Any]]], preference: str = "default") -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        abstract_blocks = []
        remaining_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_text = "".join([t["text"] for t in line]).strip()
            
            if re.match(r"^Abstract", line_text, re.IGNORECASE):
                abstract_lines = [line]
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    next_line_text = "".join([t["text"] for t in next_line]).strip()
                    # Abstract ends when we see a major section heading or a large vertical gap
                    prev_y1 = max(t["bbox"][3] for t in abstract_lines[-1])
                    curr_y0 = min(t["bbox"][1] for t in next_line)
                    
                    if (curr_y0 - prev_y1) > self.median_size * 2.0 or re.match(r"^\d+\.", next_line_text):
                        break
                    
                    abstract_lines.append(next_line)
                    j += 1
                abstract_blocks.append(self._create_block(abstract_lines))
                i = j
                continue
            
            remaining_lines.append(line)
            i += 1
            
        return abstract_blocks, remaining_lines

    def _create_block(self, lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        import copy
        return {
            "type": "abstract",
            "bbox": bbox,
            "lines": [{"spans": copy.deepcopy(l), "bbox": bbox} for l in lines],
            "text": " ".join(["".join([t["text"] for t in l]).strip() for l in lines])
        }

