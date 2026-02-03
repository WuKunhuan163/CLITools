from typing import List, Dict, Any, Tuple
import re

class LayoutEngine:
    """
    Advanced layout analysis engine using token-level coordinates and recursive zone detection.
    """
    
    def __init__(self, page_width: float, page_height: float):
        self.page_width = page_width
        self.page_height = page_height

    def segment_tokens(self, tokens: List[Dict[str, Any]], depth: int = 0) -> List[Dict[str, Any]]:
        if not tokens: return []
        if depth > 10: # Safety break
            return self._cluster_tokens_into_blocks(tokens)

        # 1. Top-level Header/Footer detection (only at depth 0)
        header_blocks = []
        footer_blocks = []
        body_tokens = tokens
        
        if depth == 0:
            header_y_limit = self.page_height * 0.05
            footer_y_limit = self.page_height * 0.95
            
            header_t = []
            footer_t = []
            new_body_t = []
            for t in tokens:
                mid_y = (t['bbox'][1] + t['bbox'][3]) / 2
                if mid_y < header_y_limit:
                    header_t.append(t)
                elif mid_y > footer_y_limit:
                    footer_t.append(t)
                else:
                    new_body_t.append(t)
            
            body_tokens = new_body_t
            if header_t:
                header_blocks = self._cluster_tokens_into_blocks(header_t)
            if footer_t:
                footer_blocks = self._cluster_tokens_into_blocks(footer_t)

        if not body_tokens:
            return header_blocks + footer_blocks

        # 2. Check for Global Vertical Gutter
        x_min = min(t['bbox'][0] for t in body_tokens)
        x_max = max(t['bbox'][2] for t in body_tokens)
        gutters = self._find_gutters(body_tokens, x_min, x_max)
        
        mid_x = (x_min + x_max) / 2
        best_global_gutter = None
        for g0, g1 in sorted(gutters, key=lambda g: g[1] - g[0], reverse=True):
            center = (g0 + g1) / 2
            if abs(center - mid_x) < (x_max - x_min) * 0.2:
                best_global_gutter = (g0, g1)
                break
        
        if best_global_gutter:
            g_mid = (best_global_gutter[0] + best_global_gutter[1]) / 2
            left_t = [t for t in body_tokens if t['bbox'][2] <= g_mid]
            right_t = [t for t in body_tokens if t['bbox'][0] >= g_mid]
            
            # Progress check: children must be strictly smaller
            if left_t and right_t and (len(left_t) < len(body_tokens)) and (len(right_t) < len(body_tokens)):
                return header_blocks + self.segment_tokens(left_t, depth + 1) + self.segment_tokens(right_t, depth + 1) + footer_blocks

        # 3. If no global vertical gutter, split into horizontal strips
        lines = self._tokens_to_lines(body_tokens)
        zones = []
        curr_multi_tokens = []
        
        for line in lines:
            line_x0 = min(t['bbox'][0] for t in line)
            line_x1 = max(t['bbox'][2] for t in line)
            
            # A line is spanning if it covers a large portion of the current width
            # AND it doesn't have a significant gap near the center.
            has_central_gap = False
            for i in range(len(line) - 1):
                gap_w = line[i+1]['bbox'][0] - line[i]['bbox'][2]
                gap_center = (line[i+1]['bbox'][0] + line[i]['bbox'][2]) / 2
                if gap_w > 10 and abs(gap_center - mid_x) < (x_max - x_min) * 0.15:
                    has_central_gap = True
                    break
            
            is_spanning = (line_x1 - line_x0) > (x_max - x_min) * 0.8 and not has_central_gap
            
            if is_spanning:
                if curr_multi_tokens:
                    zones.append(('multi', curr_multi_tokens))
                    curr_multi_tokens = []
                zones.append(('spanning', line))
            else:
                curr_multi_tokens.extend(line)
        
        if curr_multi_tokens:
            zones.append(('multi', curr_multi_tokens))
            
        # Progress check: If only one multi-zone and no spanning lines, stop recursion
        if len(zones) == 1 and zones[0][0] == 'multi':
            return header_blocks + self._cluster_tokens_into_blocks(body_tokens) + footer_blocks

        final_blocks = []
        for z_type, z_tokens in zones:
            if z_type == 'spanning':
                final_blocks.append(self._create_block([z_tokens]))
            else:
                # Recursively look for gutters within this strip
                final_blocks.extend(self.segment_tokens(z_tokens, depth + 1))
                
        return header_blocks + final_blocks + footer_blocks

    def _tokens_to_lines(self, tokens: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not tokens: return []
        tokens.sort(key=lambda t: (t['bbox'][1], t['bbox'][0]))
        lines = []
        curr_line = [tokens[0]]
        for i in range(1, len(tokens)):
            prev, curr = curr_line[-1], tokens[i]
            overlap = min(prev['bbox'][3], curr['bbox'][3]) - max(prev['bbox'][1], curr['bbox'][1])
            h = min(prev['bbox'][3] - prev['bbox'][1], curr['bbox'][3] - curr['bbox'][1])
            if overlap > h * 0.4:
                curr_line.append(curr)
            else:
                lines.append(sorted(curr_line, key=lambda t: t['bbox'][0]))
                curr_line = [curr]
        lines.append(sorted(curr_line, key=lambda t: t['bbox'][0]))
        return sorted(lines, key=lambda l: min(t['bbox'][1] for t in l))

    def _find_gutters(self, tokens: List[Dict[str, Any]], x_min: float, x_max: float) -> List[Tuple[float, float]]:
        width = int(x_max - x_min) + 1
        if width <= 0: return []
        occ = [0] * width
        for t in tokens:
            x0 = int(max(0, t['bbox'][0] - x_min))
            x1 = int(min(width - 1, t['bbox'][2] - x_min))
            for x in range(x0, x1 + 1): occ[x] = 1
        
        gutters = []
        start = None
        threshold = 3
        for x in range(width):
            if occ[x] == 0:
                if start is None: start = x
            else:
                if start is not None:
                    if (x - start) >= threshold:
                        gutters.append((start + x_min, x + x_min))
                    start = None
        if start is not None:
            if (width - start) >= threshold:
                gutters.append((start + x_min, width - 1 + x_min))
        return gutters

    def _cluster_tokens_into_blocks(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tokens: return []
        lines = self._tokens_to_lines(tokens)
        all_sizes = sorted([t.get('size', 10.0) for t in tokens])
        median_size = all_sizes[len(all_sizes)//2] if all_sizes else 10.0
        
        blocks = []
        curr_b_lines = [lines[0]]
        for i in range(1, len(lines)):
            prev_y1 = max(t['bbox'][3] for t in lines[i-1])
            curr_y0 = min(t['bbox'][1] for t in lines[i])
            if (curr_y0 - prev_y1) > median_size * 0.6:
                blocks.append(self._create_block(curr_b_lines))
                curr_b_lines = [lines[i]]
            else:
                curr_b_lines.append(lines[i])
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
