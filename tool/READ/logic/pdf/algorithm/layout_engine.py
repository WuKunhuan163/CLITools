from typing import List, Dict, Any, Tuple, Optional
import re
import copy
from .semantic.title import TitleIdentifier

class LayoutEngine:
    """
    Step-by-step refactored layout engine.
    (0) Token capturing
    (1) Title identification
    Remaining tokens returned as individual items.
    """
    
    def __init__(self, page_width: float, page_height: float, median_size: float = 10.0, preference: str = "default"):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size
        self.preference = preference
        self.title_identifier = TitleIdentifier(page_width, page_height, median_size)

    def segment_tokens(self, tokens: List[Dict[str, Any]], images: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Identify Title, everything else remains as individual tokens.
        """
        if not tokens: return []
        
        # (0) Gather all tokens and group into lines for title detection
        tokens.sort(key=lambda t: (t['bbox'][1], t['bbox'][0]))
        lines = self._tokens_to_lines(tokens)
        
        # (1) Identify Title
        title_blocks, remaining_lines = self.title_identifier.identify(lines, self.preference)
        
        # Convert remaining lines back to individual tokens
        unprocessed_items = []
        for line in remaining_lines:
            for token in line:
                unprocessed_items.append({
                    "type": "unprocessed_text",
                    "bbox": token["bbox"],
                    "text": token["text"],
                    "lines": [{"spans": [token], "bbox": token["bbox"]}],
                    "segments": [[token["text"], {"bold": "bold" in token["font"].lower() or token["flags"] & 16, 
                                                  "italic": "italic" in token["font"].lower() or token["flags"] & 2,
                                                  "color": None, "size": token["size"]}] ]
                })
        
        # Images (provided as unprocessed_image items from extractor)
        if images:
            for img in images:
                unprocessed_items.append({
                    "type": "unprocessed_image",
                    "bbox": img["bbox"],
                    "text": img.get("text", "[Image]"),
                    "lines": [],
                    "is_image": True
                })
                
        return title_blocks + unprocessed_items

    def _tokens_to_lines(self, tokens: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not tokens: return []
        tokens.sort(key=lambda t: (t['bbox'][1], t['bbox'][0]))
        lines = []
        curr_line = [tokens[0]]
        for i in range(1, len(tokens)):
            prev, curr = curr_line[-1], tokens[i]
            overlap = min(prev['bbox'][3], curr['bbox'][3]) - max(prev['bbox'][1], curr['bbox'][1])
            h = min(prev['bbox'][3] - prev['bbox'][1], curr['bbox'][3] - curr['bbox'][1])
            if overlap > h * 0.6: curr_line.append(curr)
            else:
                lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
                curr_line = [curr]
        if curr_line: lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
        return sorted(lines, key=lambda l: min(t['bbox'][1] for t in l))
