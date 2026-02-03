from typing import List, Dict, Any, Tuple, Optional
import re
import copy
from ..settlement.title import TitleIdentifier
from ..settlement.header_footer import HeaderFooterIdentifier
from ..tokenization.image import ImageIdentifier
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
        merged_image_blocks, _ = self.image_identifier.identify(remaining_images, [])
        
        # 3. Tagging individual tokens
        # Tag the raw spans first
        tokens = self.name_tagger.tag_tokens(tokens)
        tokens = self.email_tagger.tag_tokens(tokens)
        tokens = self.number_tagger.tag_tokens(tokens)

        unprocessed_pool = []
        for t in tokens:
            pool_item = copy.deepcopy(t)
            pool_item["type"] = "unprocessed_text"
            # Ensure tags are present
            if "tags" not in pool_item: pool_item["tags"] = {}
            # lines for formatter compatibility
            pool_item["lines"] = [{"spans": [copy.deepcopy(t)], "bbox": t["bbox"]}]
            unprocessed_pool.append(pool_item)
            
        # 4. Settlement
        lines = self._pool_to_lines(unprocessed_pool)
        
        # 4.1 Titles
        title_blocks, remaining_lines = self.title_identifier.identify(lines, self.preference)
        all_settled.extend(title_blocks)
        
        # 4.2 Header/Footer
        hf_blocks, remaining_lines = self.hf_identifier.identify(remaining_lines)
        all_settled.extend(hf_blocks)
        
        # 4.3 Author Settlement (Based on tags and patterns)
        author_blocks = []
        body_lines = []
        for line in remaining_lines:
            line_text = "".join([t["text"] for t in line]).strip()
            line_bbox = [min(t["bbox"][0] for t in line), min(t["bbox"][1] for t in line),
                         max(t["bbox"][2] for t in line), max(t["bbox"][3] for t in line)]
            
            # Count name tags in line
            name_tag_count = sum(1 for it in line if "name" in it.get("tags", {}))
            is_by_pattern = line_text.lower().startswith("by ")
            
            # Author heuristic: Top half, and (Multiple names OR starts with "By ")
            if line_bbox[1] < self.page_height * 0.5 and (name_tag_count >= 2 or is_by_pattern):
                author_blocks.append(self._create_settled_block(line, "author"))
            else:
                body_lines.append(line)
        all_settled.extend(author_blocks)
        
        # 5. Final Remainder
        final_unprocessed_text = []
        for line in body_lines:
            for it in line: final_unprocessed_text.append(it)
        
        return all_settled + merged_image_blocks + final_unprocessed_text

    def _create_settled_block(self, line: List[Dict[str, Any]], type_hint: str) -> Dict[str, Any]:
        bbox = [min(it["bbox"][0] for it in line), min(it["bbox"][1] for it in line),
                max(it["bbox"][2] for it in line), max(it["bbox"][3] for it in line)]
        # Re-wrap spans for formatter
        formatted_lines = [{"spans": [copy.deepcopy(it)], "bbox": it["bbox"]} for it in line]
        
        # Construct segments
        from tool.READ.logic.pdf.formatter import get_span_style
        segments = []
        line_y = line[0]["origin"][1] if line else 0
        for it in line:
            style = get_span_style(it, self.median_size, line_y)
            text = it["text"]
            if not segments: segments.append([text, style])
            else:
                if segments[-1][1] == style: segments[-1][0] += text
                else: segments.append([text, style])
        
        return {
            "type": type_hint, "bbox": bbox, "lines": formatted_lines,
            "segments": segments, "text": "".join([it["text"] for it in line]).strip()
        }

    def _pool_to_lines(self, pool: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not pool: return []
        sorted_pool = sorted(pool, key=lambda x: (x['bbox'][1], x['bbox'][0]))
        lines = []
        curr_line = [sorted_pool[0]]
        for i in range(1, len(sorted_pool)):
            prev, curr = curr_line[-1], sorted_pool[i]
            overlap = min(prev['bbox'][3], curr['bbox'][3]) - max(prev['bbox'][1], curr['bbox'][1])
            h = min(prev['bbox'][3] - prev['bbox'][1], curr['bbox'][3] - curr['bbox'][1])
            if overlap > h * 0.6: curr_line.append(curr)
            else:
                lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
                curr_line = [curr]
        if curr_line: lines.append(sorted(curr_line, key=lambda x: x['bbox'][0]))
        return sorted(lines, key=lambda l: min(t['bbox'][1] for t in l))
