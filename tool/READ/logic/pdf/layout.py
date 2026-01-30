#!/usr/bin/env python3
from typing import List, Any

class ReadingOrderSorter:
    """Handles sorting of text blocks into a logical reading order."""
    
    @staticmethod
    def sort_blocks(blocks: List[Any], page_width: float, page_height: float) -> List[Any]:
        """
        Multi-stage sorting heuristic for complex paper layouts.
        """
        if not blocks:
            return []

        # 1. Position-based filtering for headers/footers (top/bottom 10%)
        header_y_limit = page_height * 0.1
        footer_y_limit = page_height * 0.9
        
        headers = []
        footers = []
        body_blocks = []
        
        for b in blocks:
            bbox = b["bbox"]
            x0, y0, x1, y1 = bbox
                
            if y1 < header_y_limit:
                headers.append(b)
            elif y0 > footer_y_limit:
                footers.append(b)
            else:
                body_blocks.append(b)
                
        # 2. Zone-based segmentation for body
        body_blocks.sort(key=lambda b: b["bbox"][1])
        
        spanning_width_threshold = page_width * 0.6
        zones = []
        current_zone = []
        
        for b in body_blocks:
            bbox = b["bbox"]
            is_spanning = (bbox[2] - bbox[0]) > spanning_width_threshold
            
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
        headers.sort(key=lambda b: b["bbox"][1])
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
                        if curr_b["bbox"][0] - prev_b["bbox"][0] > page_width * 0.05:
                            columns.append(sorted(current_col, key=lambda b: b["bbox"][1]))
                            current_col = [curr_b]
                        else:
                            current_col.append(curr_b)
                    columns.append(sorted(current_col, key=lambda b: b["bbox"][1]))
                    
                for col in columns:
                    final_sorted.extend(col)
                    
        # Footers
        footers.sort(key=lambda b: b["bbox"][1])
        final_sorted.extend(footers)
        return final_sorted

