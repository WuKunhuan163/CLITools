from typing import List, Any, Dict

class ReadingOrderSorter:
    """Handles sorting of text blocks into a logical reading order."""
    
    @staticmethod
    def sort_blocks(blocks: List[Any], page_width: float, page_height: float) -> List[Any]:
        """
        Multi-stage sorting heuristic for complex paper layouts.
        """
        if not blocks:
            return []

        # Separate into main content and potential footers/headers
        header_y_limit = page_height * 0.08
        footer_y_limit = page_height * 0.92

        headers = []
        footers = []
        main_content_blocks = []

        for b in blocks:
            bbox = b["bbox"]
            if bbox[1] < header_y_limit:
                headers.append(b)
            elif bbox[3] > footer_y_limit:
                footers.append(b)
            else:
                main_content_blocks.append(b)

        # Sort headers and footers by Y, then X
        headers.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
        footers.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

        # Process main content blocks for columns and zones
        final_sorted_blocks = []
        
        # Add headers first
        final_sorted_blocks.extend(headers)

        if main_content_blocks:
            # Sort by Y first
            main_content_blocks.sort(key=lambda b: b["bbox"][1])
            
            # Detect columns by clustering X-coordinates
            # Simple heuristic: if blocks are clearly separated horizontally
            left_col = []
            right_col = []
            mid_point = page_width / 2
            
            # A block is considered "spanning" if its width is > 80% of page width
            # OR if it's centered and wide enough
            spanning_width_threshold = page_width * 0.8
            
            for b in main_content_blocks:
                bbox = b["bbox"]
                block_width = bbox[2] - bbox[0]
                # Spanning check: width > threshold AND centered-ish
                is_spanning = block_width > spanning_width_threshold or \
                             (block_width > page_width * 0.5 and bbox[0] < page_width * 0.2 and bbox[2] > page_width * 0.8)
                
                if is_spanning:
                    # Flush current columns before adding full-width block
                    if left_col:
                        final_sorted_blocks.extend(sorted(left_col, key=lambda x: x["bbox"][1]))
                        left_col = []
                    if right_col:
                        final_sorted_blocks.extend(sorted(right_col, key=lambda x: x["bbox"][1]))
                        right_col = []
                    final_sorted_blocks.append(b)
                elif bbox[2] < mid_point + page_width * 0.02: # Tighter threshold
                    left_col.append(b)
                elif bbox[0] > mid_point - page_width * 0.02: # Tighter threshold
                    right_col.append(b)
                else:
                    # Spans both or centered but not wide enough to be 'spanning'
                    # Put in left or right based on center of gravity
                    center_x = (bbox[0] + bbox[2]) / 2
                    if center_x < mid_point: left_col.append(b)
                    else: right_col.append(b)

            # Final flush
            if left_col:
                final_sorted_blocks.extend(sorted(left_col, key=lambda x: x["bbox"][1]))
            if right_col:
                final_sorted_blocks.extend(sorted(right_col, key=lambda x: x["bbox"][1]))

        # Add footers last
        final_sorted_blocks.extend(footers)

        return final_sorted_blocks

