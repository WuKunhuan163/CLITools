#!/usr/bin/env python3
from typing import List, Dict, Any, Optional
import fitz # PyMuPDF

class ReadingOrderSorter:
    """Handles sorting of text blocks into a logical reading order."""
    
    @staticmethod
    def sort_blocks(blocks: List[Any], page_width: float, page_height: float) -> List[Any]:
        """
        Multi-stage sorting heuristic for complex paper layouts.
        Works for both blocks and lines.
        """
        if not blocks:
            return []

        # 1. Position-based filtering for headers/footers (top 5%, bottom 5%)
        header_y_limit = page_height * 0.05
        footer_y_limit = page_height * 0.95
        
        headers = []
        footers = []
        body_blocks = []
        
        for b in blocks:
            bbox = b["bbox"]
            y0, y1 = bbox[1], bbox[3]
            if y1 < header_y_limit:
                headers.append(b)
            elif y0 > footer_y_limit:
                footers.append(b)
            else:
                body_blocks.append(b)
                
        # 2. Sort body blocks by Y first
        body_blocks.sort(key=lambda b: b["bbox"][1])
        
        # 3. Detect columns and zones
        mid_x = page_width / 2
        
        # Divide into vertical zones based on full-width (spanning) blocks
        spanning_width_threshold = page_width * 0.6
        zones = []
        current_zone = []
        
        for b in body_blocks:
            bbox = b["bbox"]
            width = bbox[2] - bbox[0]
            # A block is spanning if it's wider than threshold AND centered
            is_spanning = width > spanning_width_threshold and (bbox[0] < mid_x - 50) and (bbox[2] > mid_x + 50)
            
            if is_spanning:
                if current_zone:
                    zones.append(('body', current_zone))
                    current_zone = []
                zones.append(('spanning', [b]))
            else:
                current_zone.append(b)
                
        if current_zone:
            zones.append(('body', current_zone))
            
        final_sorted = []
        # Headers
        headers.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
        final_sorted.extend(headers)
        
        # Body Zones
        for zone_type, zone_blocks in zones:
            if zone_type == 'spanning':
                final_sorted.extend(zone_blocks)
            else:
                # Sub-column detection by X clustering
                zone_blocks.sort(key=lambda b: b["bbox"][0])
                columns = []
                if zone_blocks:
                    current_col = [zone_blocks[0]]
                    for i in range(1, len(zone_blocks)):
                        prev_b = zone_blocks[i-1]
                        curr_b = zone_blocks[i]
                        # If the horizontal gap between starts is significant, it's a new column
                        if curr_b["bbox"][0] - prev_b["bbox"][0] > page_width * 0.05:
                            columns.append(sorted(current_col, key=lambda b: b["bbox"][1]))
                            current_col = [curr_b]
                        else:
                            current_col.append(curr_b)
                    columns.append(sorted(current_col, key=lambda b: b["bbox"][1]))
                    
                for col in columns:
                    final_sorted.extend(col)
                    
        # Footers
        footers.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
        final_sorted.extend(footers)
        return final_sorted

def parse_page_spec(spec: Optional[str], total_pages: int) -> List[int]:
    """Parse page specification like '1,3,5-7'."""
    pages = []
    if not spec:
        return list(range(total_pages))
        
    for part in spec.split(','):
        part = part.strip()
        if not part: continue
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                pages.extend(range(max(0, start - 1), min(total_pages, end)))
            except: pass
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    pages.append(p - 1)
            except: pass
    return sorted(list(set(pages)))

def get_median_font_size(blocks: List[Any]) -> float:
    """Calculate the median font size of all text spans on the page."""
    sizes = []
    for b in blocks:
        if b.get("type") != 0: continue
        for line in b["lines"]:
            for span in line["spans"]:
                if span["text"].strip():
                    sizes.append(span["size"])
    if not sizes: return 12.0
    sizes.sort()
    return sizes[len(sizes) // 2]
