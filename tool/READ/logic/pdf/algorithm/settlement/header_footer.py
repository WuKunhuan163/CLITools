from typing import List, Dict, Any, Tuple, Optional
import re
import copy
from .utils import create_settled_block

class HeaderFooterIdentifier:
    """
    Identifies headers and footers based on vertical gaps and content (like DOI).
    The gap is relative to the height of the text line.
    """
    
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size
        self.doi_regex = re.compile(r"DOI:? *10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+", re.IGNORECASE)

    def identify(self, lines: List[List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        """
        Identifies header and footer blocks using relative gaps.
        """
        if not lines:
            return [], []

        # Sort lines by Y coordinate
        sorted_lines = sorted(lines, key=lambda l: min(t["bbox"][1] for t in l))
        
        # Calculate gaps and line heights
        line_data = []
        for l in sorted_lines:
            # Skip separator lines
            if len(l) == 1 and l[0].get("type") == "separator":
                line_data.append({"type": "separator", "bbox": l[0]["bbox"], "height": 0, "text": ""})
                continue
            bbox = self._get_line_bbox(l)
            line_data.append({
                "bbox": bbox,
                "height": bbox[3] - bbox[1],
                "text": " ".join(t["text"] for t in l).strip()
            })
            
        header_end_idx = 0
        footer_start_idx = len(sorted_lines)
        
        # 1. Detect Header (Top-down)
        for i in range(min(5, len(sorted_lines) - 1)):
            curr = line_data[i]
            if curr.get("type") == "separator": continue

            next_l = line_data[i+1]
            if next_l.get("type") == "separator": continue

            gap = next_l["bbox"][1] - curr["bbox"][3]
            
            # Content heuristic (DOI)
            if self.doi_regex.search(curr["text"]):
                header_end_idx = i + 1
                # Check if we should include more lines? Usually DOI is the end of header
                # but if there's no gap, we might keep looking. Trust the gap.
                if gap > curr["height"] * 1.1:
                    break
                continue

            # Gap heuristic: gap is larger than text height
            if gap > curr["height"] * 1.1:
                header_end_idx = i + 1
                break
        
        # 2. Detect Footer (Bottom-up)
        for i in range(len(sorted_lines) - 1, max(0, len(sorted_lines) - 6), -1):
            curr = line_data[i]
            prev_l = line_data[i-1]
            gap = curr["bbox"][1] - prev_l["bbox"][3]
            
            if self.doi_regex.search(curr["text"]):
                footer_start_idx = i
                if gap > curr["height"] * 1.1:
                    break
                continue

            if gap > curr["height"] * 1.1:
                footer_start_idx = i
                break
        
        identified_blocks = []
        
        # Avoid identifying the whole page as header/footer if gaps are large everywhere
        # (e.g. sparse page). Ensure they are in respective halves.
        for i in range(header_end_idx):
            if line_data[i]["bbox"][3] < self.page_height * 0.5:
                identified_blocks.append(create_settled_block([sorted_lines[i]], "header", self.median_size))
            else:
                header_end_idx = i # Stop here
                break
            
        for i in range(footer_start_idx, len(sorted_lines)):
            if line_data[i]["bbox"][1] > self.page_height * 0.5:
                identified_blocks.append(create_settled_block([sorted_lines[i]], "footer", self.median_size))
            else:
                footer_start_idx = i + 1 # Adjust body start
                break
            
        body_lines = sorted_lines[header_end_idx:footer_start_idx]
        
        # Post-process for subtype (DOI)
        for block in identified_blocks:
            if self.doi_regex.search(block["text"]):
                block["subtype"] = "DOI"

        return identified_blocks, body_lines

    def _get_line_bbox(self, line: List[Dict[str, Any]]) -> List[float]:
        return [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
