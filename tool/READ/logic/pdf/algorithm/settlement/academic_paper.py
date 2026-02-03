from typing import List, Dict, Any, Tuple, Optional
import re
import copy
from ..settlement.title import TitleIdentifier
from ..settlement.header_footer import HeaderFooterIdentifier
from ..settlement.utils import create_settled_block
from ..tokenization.image import ImageIdentifier
from ..tokenization.reading_order import ReadingOrderIdentifier
from ..tagging.name import NameIdentifier
from ..tagging.email import EmailIdentifier
from ..tagging.number import NumberIdentifier

class LayoutEngine:
    """
    Standard layout engine for Academic Papers.
    """
    def __init__(self, page_width: float, page_height: float, median_size: float = 10.0, preference: str = "default"):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size
        self.preference = preference
        self.title_identifier = TitleIdentifier(page_width, page_height, median_size)
        self.hf_identifier = HeaderFooterIdentifier(page_width, page_height, median_size)
        self.image_identifier = ImageIdentifier(page_width, page_height, median_size)
        self.reading_order_identifier = ReadingOrderIdentifier(page_width, page_height, median_size)
        self.name_tagger = NameIdentifier(median_size)
        self.email_tagger = EmailIdentifier()
        self.number_tagger = NumberIdentifier()

    def segment_tokens(self, tokens: List[Dict[str, Any]], images: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        all_settled = []
        
        # 1. Separators
        remaining_images = []
        separators = []
        if images:
            for i, img in enumerate(images):
                bbox = img["bbox"]
                w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
                aspect_ratio = max(w/h, h/w) if h > 0 and w > 0 else 0
                
                # Heuristic: extreme aspect ratio and thin
                is_sep = aspect_ratio > 20 and min(w, h) < 6.0
                
                # Check for overlap with other images (separators should be isolated)
                if is_sep:
                    has_major_overlap = False
                    for j, other in enumerate(images):
                        if i == j: continue
                        o_bbox = other["bbox"]
                        # Intersection
                        ix = [max(bbox[0], o_bbox[0]), max(bbox[1], o_bbox[1]), min(bbox[2], o_bbox[2]), min(bbox[3], o_bbox[3])]
                        if ix[2] > ix[0] and ix[3] > ix[1]:
                            area_ix = (ix[2]-ix[0]) * (ix[3]-ix[1])
                            area_sep = w * h
                            if area_ix > area_sep * 0.5:
                                has_major_overlap = True
                                break
                    if not has_major_overlap:
                        separators.append({"type": "separator", "bbox": bbox, "text": "[Separator Line]", "lines": []})
                        continue
                remaining_images.append(img)
        all_settled.extend(separators)
        
        # 2. Image Assembly
        merged_image_blocks, tokens = self.image_identifier.identify(remaining_images, tokens)
        
        # 3. Reading Order Prediction
        # This will also synthesize separators if gutters are found
        tokens, _ = self.reading_order_identifier.predict_order(tokens, separators)

        # 4. Tagging individual tokens
        # Tag the ordered tokens
        tokens = self.name_tagger.tag_tokens(tokens)
        tokens = self.email_tagger.tag_tokens(tokens)
        tokens = self.number_tagger.tag_tokens(tokens)

        # 5. Settlement
        lines = self._pool_to_lines(tokens)
        
        # 5.1 Titles
        title_blocks, remaining_lines = self.title_identifier.identify(lines, self.preference)
        all_settled.extend(title_blocks)
        
        # 5.2 Header/Footer
        hf_blocks, remaining_lines = self.hf_identifier.identify(remaining_lines)
        all_settled.extend(hf_blocks)
        
        # 5.3 Author Settlement (Based on tags and patterns)
        author_blocks = []
        body_lines = []
        for line in remaining_lines:
            # Check if this is a separator line
            if len(line) == 1 and line[0].get("type") == "separator":
                body_lines.append(line)
                continue

            line_text = "".join([t["text"] for t in line]).strip()
            line_bbox = [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                         max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
            
            # Count name tags in line
            name_tag_count = sum(1 for it in line if "name" in it.get("tags", {}))
            is_by_pattern = line_text.lower().startswith("by ")
            
            # Author heuristic: Top half, and (Multiple names OR starts with "By ")
            if line_bbox[1] < self.page_height * 0.5 and (name_tag_count >= 2 or is_by_pattern):
                author_blocks.append(create_settled_block([line], "author", self.median_size))
            else:
                body_lines.append(line)
        all_settled.extend(author_blocks)
        
        # 6. Final Remainder
        final_unprocessed_text = []
        for line in body_lines:
            for it in line:
                if it.get("type") != "separator":
                    it["type"] = "unprocessed_text"
                final_unprocessed_text.append(it)
        
        return all_settled + merged_image_blocks + final_unprocessed_text

    def _pool_to_lines(self, pool: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not pool: return []
        # Trust the input pool order (which is already reading order from predict_order)
        # We only want to group adjacent tokens into horizontal lines where appropriate.
        lines = []
        curr_line = []
        for t in pool:
            if t.get("type") == "separator":
                if curr_line:
                    lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
                    curr_line = []
                lines.append([t])
                continue

            if not curr_line:
                curr_line = [t]
                continue

            prev = curr_line[-1]
            # Vertical overlap check
            overlap = min(prev['bbox'][3], t['bbox'][3]) - max(prev['bbox'][1], t['bbox'][1])
            h = min(prev['bbox'][3] - prev['bbox'][1], t['bbox'][3] - t['bbox'][1])
            
            # Horizontal distance check - if moving backwards or too far, it's a new line
            dist_x = t['bbox'][0] - prev['bbox'][2]
            
            if overlap > h * 0.5 and dist_x > -self.page_width * 0.1 and dist_x < self.page_width * 0.3:
                curr_line.append(t)
            else:
                lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
                curr_line = [t]
        
        if curr_line:
            lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
        
        return lines
