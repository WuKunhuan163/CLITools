import re
from typing import List, Dict, Any, Tuple

class FooterIdentifier:
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size

    def identify(self, lines: List[List[Dict[str, Any]]], preference: str = "default") -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        footer_blocks = []
        remaining_lines = []
        
        for line in lines:
            line_bbox = [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                         max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
            
            # Bottom 6% of the page
            if line_bbox[1] > self.page_height * 0.94:
                footer_blocks.append(self._create_block([line]))
            else:
                remaining_lines.append(line)
        return footer_blocks, remaining_lines

    def _create_block(self, lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        import copy
        return {
            "type": "footer",
            "bbox": bbox,
            "lines": [{"spans": copy.deepcopy(l), "bbox": bbox} for l in lines],
            "text": "".join([t["text"] for l in lines for t in l]).strip()
        }

