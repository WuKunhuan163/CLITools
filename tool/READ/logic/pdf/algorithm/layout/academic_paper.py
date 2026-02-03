from typing import List, Dict, Any, Tuple, Optional
import re
import copy
from ..semantic.title import TitleIdentifier
from ..semantic.header_footer import HeaderFooterIdentifier
from ..semantic.image import ImageIdentifier
from ..semantic.author import AuthorIdentifier

class LayoutEngine:
    """
    Standard layout engine for Academic Papers.
    
    PHASE A: Tokenization
    - Pixel Saliency (handled in extractor)
    - Separator identification
    - Image assembly & Smart text absorption (RECORDING absorbed texts)
    
    PHASE B: Non-Reading-Order Settlement
    - Title identification
    - Header/Footer identification
    - Author identification
    """
    
    def __init__(self, page_width: float, page_height: float, median_size: float = 10.0, preference: str = "default"):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size
        self.preference = preference
        
        # Identifiers
        self.title_identifier = TitleIdentifier(page_width, page_height, median_size)
        self.hf_identifier = HeaderFooterIdentifier(page_width, page_height, median_size)
        self.image_identifier = ImageIdentifier(page_width, page_height, median_size)
        self.author_identifier = AuthorIdentifier(page_width, page_height, median_size)

    def segment_tokens(self, tokens: List[Dict[str, Any]], images: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Main pipeline executing Phase A and Phase B.
        """
        if not tokens and not images: return []
        
        # --- PHASE A: Tokenization ---
        
        # 1. Separators
        remaining_images = []
        separators = []
        if images:
            for img in images:
                bbox = img["bbox"]
                w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
                aspect_ratio = max(w/h, h/w) if h > 0 and w > 0 else 0
                if aspect_ratio > 20 and min(w, h) < 4.0:
                    separators.append({
                        "type": "separator", "bbox": bbox, "text": "[Separator Line]", "lines": []
                    })
                else:
                    remaining_images.append(img)
        
        # 2. Image Assembly & Smart Text Absorption
        merged_image_blocks, remaining_tokens = self.image_identifier.identify(remaining_images, tokens)
        
        # --- PHASE B: Non-Reading-Order Settlement ---
        
        # Prepare lines for settlement identifiers
        remaining_tokens.sort(key=lambda t: (t['bbox'][1], t['bbox'][0]))
        lines = self._tokens_to_lines(remaining_tokens)
        
        # 3. Titles
        title_blocks, remaining_lines = self.title_identifier.identify(lines, self.preference)
        
        # 4. Header/Footer
        hf_blocks, remaining_lines = self.hf_identifier.identify(remaining_lines)
        
        # 5. Author identification (New Step)
        author_blocks, remaining_lines = self.author_identifier.identify(remaining_lines, self.preference)
        
        # --- FINAL ASSEMBLY ---
        
        # Body content (Unprocessed Remainder)
        unprocessed_text_items = []
        for line in remaining_lines:
            for token in line:
                unprocessed_text_items.append({
                    "type": "unprocessed_text",
                    "bbox": token["bbox"],
                    "text": token["text"],
                    "lines": [{"spans": [token], "bbox": token["bbox"]}],
                    "segments": [[token["text"], {
                        "bold": "bold" in token["font"].lower() or token["flags"] & 16, 
                        "italic": "italic" in token["font"].lower() or token["flags"] & 2,
                        "color": None, "size": token["size"],
                        "super": False, "sub": False
                    }]]
                })
        
        return (separators + merged_image_blocks + title_blocks + 
                hf_blocks + author_blocks + unprocessed_text_items)

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

    def _get_lines_bbox(self, lines: List[List[Dict[str, Any]]]) -> List[float]:
        all_t = [t for l in lines for t in l]
        if not all_t: return [0, 0, 0, 0]
        return [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t), max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
