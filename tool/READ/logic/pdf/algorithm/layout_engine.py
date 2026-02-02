from typing import List, Dict, Any, Tuple
import re

class LayoutEngine:
    """
    Advanced layout analysis engine using token-level coordinates and gutter detection.
    """
    
    def __init__(self, page_width: float, page_height: float):
        self.page_width = page_width
        self.page_height = page_height

    def segment_tokens(self, tokens: List[Dict[str, Any]], depth: int = 0) -> List[Dict[str, Any]]:
        """
        Recursively segment tokens into columns and blocks.
        """
        if not tokens: return []

        # 1. Position-based filtering for headers/footers (top 5%, bottom 5%)
        # Only do this at the top level
        body_tokens = tokens
        header_blocks = []
        footer_blocks = []
        if depth == 0:
            header_y_limit = self.page_height * 0.05
            footer_y_limit = self.page_height * 0.95
            
            body_tokens = []
            header_t = []
            footer_t = []
            for t in tokens:
                if t['bbox'][3] < header_y_limit:
                    header_t.append(t)
                elif t['bbox'][1] > footer_y_limit:
                    footer_t.append(t)
                else:
                    body_tokens.append(t)
            
            if header_t:
                header_blocks = self._cluster_tokens_into_blocks(header_t)
            if footer_t:
                footer_blocks = self._cluster_tokens_into_blocks(footer_t)

        if not body_tokens:
            return header_blocks + footer_blocks

        # 2. Detect Gutter
        x_min = min(t['bbox'][0] for t in body_tokens)
        x_max = max(t['bbox'][2] for t in body_tokens)
        
        gutters = self._find_gutters(body_tokens, x_min, x_max)
        # Pick the most "central" and "significant" gutter
        mid_x = (x_min + x_max) / 2
        
        # A gutter is significant if it's wide enough and somewhat central
        significant_gutters = [g for g in gutters if (g[1] - g[0]) > 15] # at least 15 units wide
        
        if significant_gutters and depth < 2:
            # Pick the one closest to the center
            best_gutter = min(significant_gutters, key=lambda g: abs((g[0] + g[1])/2 - mid_x))
            gutter_mid = (best_gutter[0] + best_gutter[1]) / 2
            
            left_t = [t for t in body_tokens if t['bbox'][2] <= gutter_mid]
            right_t = [t for t in body_tokens if t['bbox'][0] >= gutter_mid]
            
            # Check if we actually split anything
            if left_t and right_t:
                return header_blocks + self.segment_tokens(left_t, depth + 1) + self.segment_tokens(right_t, depth + 1) + footer_blocks

        # 3. No significant gutter found, or max depth reached
        # Segment vertically into blocks
        return header_blocks + self._cluster_tokens_into_blocks(body_tokens) + footer_blocks

    def _cluster_tokens_into_blocks(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tokens: return []
        lines = self._tokens_to_lines(tokens)
        
        blocks = []
        if not lines: return []
        
        curr_b_lines = [lines[0]]
        for i in range(1, len(lines)):
            prev_l, curr_l = curr_b_lines[-1], lines[i]
            prev_y1 = max(t['bbox'][3] for t in prev_l)
            curr_y0 = min(t['bbox'][1] for t in curr_l)
            
            y_gap = curr_y0 - prev_y1
            
            # Heuristic for paragraph break: larger gap than usual line spacing
            # Use median font size as reference
            all_t = [t for l in lines for t in l]
            median_size = sorted([t.get('size', 10.0) for t in all_t])[len(all_t)//2] if all_t else 10.0
            
            if y_gap < median_size * 0.5: # Tight gap, same block
                curr_b_lines.append(curr_l)
            else:
                blocks.append(self._create_block(curr_b_lines))
                curr_b_lines = [curr_l]
        
        blocks.append(self._create_block(curr_b_lines))
        return blocks

    def _create_block(self, lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_t = [t for l in lines for t in l]
        bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
        formatted_lines = []
        for line_t in lines:
            spans = []
            for t in line_t:
                spans.append({
                    "text": t['text'], "bbox": t['bbox'], "font": t.get('font', 'Arial'),
                    "size": t.get('size', 10.0), "color": t.get('color', 0),
                    "flags": t.get('flags', 0), "origin": t.get('origin', (t['bbox'][0], t['bbox'][3]))
                })
            formatted_lines.append({"spans": spans, "bbox": [
                min(s['bbox'][0] for s in spans), min(s['bbox'][1] for s in spans),
                max(s['bbox'][2] for s in spans), max(s['bbox'][3] for s in spans)
            ]})
        return {"bbox": bbox, "lines": formatted_lines}
