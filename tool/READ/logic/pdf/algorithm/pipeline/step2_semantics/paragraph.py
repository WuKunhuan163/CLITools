import numpy as np
from typing import List, Dict, Any, Tuple, Optional

class ParagraphEngine:
    def __init__(self, median_size: float):
        self.median_size = median_size

    def is_on_same_line(self, t1: Dict[str, Any], t2: Dict[str, Any], median_h: float) -> bool:
        """Determines if two tokens are on the same horizontal line."""
        vertical_tolerance = median_h * 0.5
        b1 = t1.get("glyph_bbox", t1["bbox"])
        b2 = t2.get("glyph_bbox", t2["bbox"])
        return abs(b1[1] - b2[1]) < vertical_tolerance

    def are_close_horizontally(self, t1: Dict[str, Any], t2: Dict[str, Any], median_h: float) -> bool:
        """Determines if two tokens are close enough to be in the same line/sentence."""
        b1 = t1.get("glyph_bbox", t1["bbox"])
        b2 = t2.get("glyph_bbox", t2["bbox"])
        # Assume t1 is before t2 horizontally
        gap = b2[0] - b1[2]
        return gap < median_h * 1.5

    def get_line_span(self, tokens: List[Dict[str, Any]]) -> List[float]:
        if not tokens: return [0, 0, 0, 0]
        bboxes = [t.get("glyph_bbox", t["bbox"]) for t in tokens]
        return [
            min(b[0] for b in bboxes),
            min(b[1] for b in bboxes),
            max(b[2] for b in bboxes),
            max(b[3] for b in bboxes)
        ]

    def merge_paragraphs(self, ordered_tokens: List[Dict[str, Any]], median_h: float) -> List[Dict[str, Any]]:
        """
        Organizes tokens into paragraphs using the requested two-case algorithm.
        Returns a list of blocks, where each block is {"type": "paragraph"|"image", "tokens": [...]}.
        """
        if not ordered_tokens: return []

        blocks = []
        curr_block_tokens = []
        
        # Pre-group tokens into their raw PDF blocks if they have block_id
        raw_pdf_blocks = {}
        for t in ordered_tokens:
            bid = t.get("block_id")
            if bid is not None:
                if bid not in raw_pdf_blocks: raw_pdf_blocks[bid] = []
                raw_pdf_blocks[bid].append(t)

        def get_block_info(token):
            bid = token.get("block_id")
            if bid is None: return None
            btks = raw_pdf_blocks.get(bid, [])
            lines = {}
            for bt in btks:
                lid = bt.get("line_id")
                if lid not in lines: lines[lid] = []
                lines[lid].append(bt)
            return {"tokens": btks, "lines": lines}

        for i, tk in enumerate(ordered_tokens):
            if tk["type"] == "visual":
                if curr_block_tokens:
                    blocks.append({"type": "paragraph", "tokens": curr_block_tokens})
                    curr_block_tokens = []
                blocks.append({"type": "image", "tokens": [tk]})
                continue

            # It's a text token
            if not curr_block_tokens:
                curr_block_tokens.append(tk)
                continue

            prev = curr_block_tokens[-1]
            
            # CASE 1: Same line connection
            if self.is_on_same_line(prev, tk, median_h) and self.are_close_horizontally(prev, tk, median_h):
                curr_block_tokens.append(tk)
                continue

            # CASE 2: Line break connection
            merged = False
            prev_info = get_block_info(prev)
            if prev_info:
                lid = prev.get("line_id")
                line_tkns = prev_info["lines"].get(lid, [])
                line_tkns.sort(key=lambda t: t.get("glyph_bbox", t["bbox"])[0])
                
                if line_tkns and line_tkns[-1]["id"] == prev["id"]:
                    line_span = self.get_line_span(line_tkns)
                    pb = prev.get("glyph_bbox", prev["bbox"])
                    
                    # Condition B: Previous token's end near end of line span
                    if abs(pb[2] - line_span[2]) < median_h * 1.5: 
                        tk_b = tk.get("glyph_bbox", tk["bbox"])
                        block_span = self.get_line_span(prev_info["tokens"])
                        
                        # Condition C: Next token near start of block span
                        if abs(tk_b[0] - block_span[0]) < median_h * 2.5: 
                            # Condition D: Vertical distance matches
                            v_gap = tk_b[1] - pb[3]
                            if 0 < v_gap < median_h * 1.8:
                                merged = True

            if merged:
                curr_block_tokens.append(tk)
            else:
                # Start new paragraph
                blocks.append({"type": "paragraph", "tokens": curr_block_tokens})
                curr_block_tokens = [tk]

        if curr_block_tokens:
            blocks.append({"type": "paragraph", "tokens": curr_block_tokens})

        return blocks
