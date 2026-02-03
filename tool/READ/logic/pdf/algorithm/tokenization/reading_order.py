import numpy as np
from typing import List, Dict, Any, Tuple

class ReadingOrderIdentifier:
    """
    Predicts reading order by identifying columns and vertical splits.
    Synthesizes separators if high-confidence gutters are found.
    """
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size

    def predict_order(self, tokens: List[Dict[str, Any]], existing_separators: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not tokens: return [], []

        # 1. Group into lines to detect gutters per line
        lines = self._group_into_lines(tokens)
        
        # 2. Count line gaps at each X coordinate in the middle section
        search_start = int(self.page_width * 0.25)
        search_end = int(self.page_width * 0.75)
        gap_scores = np.zeros(int(self.page_width) + 1)
        
        total_lines = len(lines)
        for line in lines:
            line_occupied = np.zeros(int(self.page_width) + 1)
            for t in line:
                start = max(0, int(t["bbox"][0]))
                end = min(int(self.page_width), int(t["bbox"][2]))
                line_occupied[start:end+1] = 1
            
            # Find gaps in this line
            in_gap = False
            start_x = 0
            for x in range(search_start, search_end):
                if line_occupied[x] == 0:
                    if not in_gap:
                        in_gap = True
                        start_x = x
                else:
                    if in_gap:
                        width = x - start_x
                        if width > self.median_size * 0.5:
                            gap_scores[start_x:x+1] += 1
                        in_gap = False
            if in_gap:
                width = search_end - start_x
                if width > self.median_size * 0.5:
                    gap_scores[start_x:search_end+1] += 1

        # 3. Find the best gutter (highest score and significant width)
        best_gx1, best_gx2 = 0, 0
        best_score = 0
        
        in_gutter = False
        start_x = 0
        for x in range(search_start, search_end):
            # If at least 40% of lines have a gap here, it's a potential gutter
            if gap_scores[x] > total_lines * 0.4:
                if not in_gutter:
                    in_gutter = True
                    start_x = x
            else:
                if in_gutter:
                    width = x - start_x
                    score = np.mean(gap_scores[start_x:x+1])
                    if width >= self.median_size * 0.8 and score > best_score:
                        best_score = score
                        best_gx1, best_gx2 = start_x, x
                    in_gutter = False
        if in_gutter:
            width = search_end - start_x
            score = np.mean(gap_scores[start_x:search_end+1])
            if width >= self.median_size * 0.8 and score > best_score:
                best_gx1, best_gx2 = start_x, search_end

        confirmed_gutters = []
        if best_score > 0:
            confirmed_gutters.append((best_gx1, best_gx2))

        synthesized_separators = []
        for gx1, gx2 in confirmed_gutters:
            mid_x = (gx1 + gx2) / 2
            # Find the vertical extent of the gutter by looking at tokens that respect it
            left_side = [t for t in tokens if t["bbox"][2] <= gx1 + 5]
            right_side = [t for t in tokens if t["bbox"][0] >= gx2 - 5]
            
            if left_side and right_side:
                y_min = max(min(t["bbox"][1] for t in left_side), min(t["bbox"][1] for t in right_side))
                y_max = min(max(t["bbox"][3] for t in left_side), max(t["bbox"][3] for t in right_side))
                
                synthesized_separators.append({
                    "type": "separator",
                    "subtype": "column_gutter",
                    "bbox": [gx1 + (gx2-gx1)*0.4, y_min, gx2 - (gx2-gx1)*0.4, y_max],
                    "text": "[Synthesized Column Gutter]",
                    "lines": [],
                    "rationale": f"Consistent vertical gap detected at x={mid_x:.1f} across {best_score:.1f} lines"
                })

        # 4. Sorting with column awareness
        if confirmed_gutters:
            gutter = confirmed_gutters[0]
            mid_x = (gutter[0] + gutter[1]) / 2
            
            # Bands are already grouped into lines
            ordered_tokens = []
            column_buffer = [] # Buffer for consecutive columned lines
            
            def flush_column_buffer():
                if not column_buffer: return
                c1, c2 = [], []
                for line in column_buffer:
                    for t in line:
                        if t["bbox"][2] < mid_x: c1.append(t)
                        else: c2.append(t)
                ordered_tokens.extend(sorted(c1, key=lambda t: (t["bbox"][1], t["bbox"][0])))
                for sep in synthesized_separators: ordered_tokens.append(sep)
                ordered_tokens.extend(sorted(c2, key=lambda t: (t["bbox"][1], t["bbox"][0])))
                column_buffer.clear()

            for i, line in enumerate(lines):
                line_bbox = [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                             max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
                
                # Check if any token in this line actually occupies the gutter space
                has_token_in_gutter = any(t["bbox"][0] < (gutter[1]-2) and t["bbox"][2] > (gutter[0]+2) for t in line)
                
                # If the line has tokens in the gutter, it's a spanning line (like Title)
                if has_token_in_gutter:
                    flush_column_buffer()
                    ordered_tokens.extend(sorted(line, key=lambda t: t["bbox"][0]))
                else:
                    # Line is likely split into columns
                    column_buffer.append(line)
            flush_column_buffer()
        else:
            ordered_tokens = sorted(tokens, key=lambda t: (t["bbox"][1], t["bbox"][0]))

        return ordered_tokens, synthesized_separators

    def _group_into_lines(self, tokens: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not tokens: return []
        sorted_t = sorted(tokens, key=lambda x: (x['bbox'][1], x['bbox'][0]))
        lines = []
        curr_line = [sorted_t[0]]
        for i in range(1, len(sorted_t)):
            prev, curr = curr_line[-1], sorted_t[i]
            overlap = min(prev['bbox'][3], curr['bbox'][3]) - max(prev['bbox'][1], curr['bbox'][1])
            h = min(prev['bbox'][3] - prev['bbox'][1], curr['bbox'][3] - curr['bbox'][1])
            if overlap > h * 0.5:
                curr_line.append(curr)
            else:
                lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
                curr_line = [curr]
        if curr_line: lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
        return lines
