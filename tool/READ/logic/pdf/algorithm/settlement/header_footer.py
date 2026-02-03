from typing import List, Dict, Any, Tuple, Optional
import re
import copy

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
            bbox = self._get_line_bbox(l)
            line_data.append({
                "bbox": bbox,
                "height": bbox[3] - bbox[1],
                "text": "".join(t["text"] for t in l).strip()
            })
            
        header_end_idx = 0
        footer_start_idx = len(sorted_lines)
        
        # 1. Detect Header (Top-down)
        for i in range(min(5, len(sorted_lines) - 1)):
            curr = line_data[i]
            next_l = line_data[i+1]
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
                identified_blocks.append(self._create_block([sorted_lines[i]], "header"))
            else:
                header_end_idx = i # Stop here
                break
            
        for i in range(footer_start_idx, len(sorted_lines)):
            if line_data[i]["bbox"][1] > self.page_height * 0.5:
                identified_blocks.append(self._create_block([sorted_lines[i]], "footer"))
            else:
                footer_start_idx = i + 1 # Adjust body start
                break
            
        body_lines = sorted_lines[header_end_idx:footer_start_idx]
        
        return identified_blocks, body_lines

    def _get_line_bbox(self, line: List[Dict[str, Any]]) -> List[float]:
        return [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]

    def _create_block(self, lines: List[List[Dict[str, Any]]], type_hint: str) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        
        from tool.READ.logic.pdf.formatter import get_span_style
        
        formatted_lines = [{"spans": copy.deepcopy(l), "bbox": self._get_line_bbox(l)} for l in lines]
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

        text = " ".join(["".join([t["text"] for t in l]).strip() for l in lines])
        subtype = "DOI" if self.doi_regex.search(text) else None

        return {
            "type": type_hint, "subtype": subtype, "bbox": bbox,
            "lines": formatted_lines, "segments": segments, "text": text
        }
