import re
from typing import List, Dict, Any, Tuple

def identify_block_type(block: Dict[str, Any], page_rect: Any, median_size: float) -> str:
    """
    Identifies the semantic type of a block (title, heading, paragraph, etc.)
    """
    bbox = block["bbox"]
    text = "".join([s["text"] for line in block["lines"] for s in line["spans"]]).strip()
    
    # 1. Image detection (already handled by ImageIdentifier, but safety check)
    if block.get("is_image"): return "image"
    
    # 2. Header/Footer detection
    # Top/Bottom 10% of the page
    margin = page_rect.height * 0.1
    if bbox[3] < margin: return "header"
    if bbox[1] > page_rect.height - margin: return "footer"
    
    # 3. Title/Heading detection
    max_size = 0
    for line in block["lines"]:
        for span in line["spans"]:
            max_size = max(max_size, span["size"])
            
    if max_size > median_size * 1.5:
        # Check if it's centered
        page_mid = page_rect.width / 2
        block_mid = (bbox[0] + bbox[2]) / 2
        if abs(block_mid - page_mid) < page_rect.width * 0.1:
            return "title"
        return "heading"
    
    if max_size > median_size * 1.1:
        return "heading"
    
    # 4. Reference detection
    if re.match(r'^\[\d+\]', text) or re.match(r'^\d+\.', text):
        # Additional checks might be needed to distinguish from list items
        return "reference"
        
    return "paragraph"

class Tagger:
    """
    Handles semantic tagging and merging of blocks.
    """
    def __init__(self, page_rect: Any, median_size: float):
        self.page_rect = page_rect
        self.median_size = median_size

    def tag_and_merge(self, grouped_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Phase 1: Initial Tagging
        semantic_items = []
        in_reference_section = False
        
        for b in grouped_blocks:
            b_type = identify_block_type(b, self.page_rect, self.median_size)
            
            # State-based refinement
            if b_type == "reference": in_reference_section = True
            elif in_reference_section and b_type not in ["heading", "title", "footer", "header"]:
                b_type = "reference"
            
            # Simple segment extraction
            segments = []
            for line in b["lines"]:
                for span in line["spans"]:
                    segments.append([span["text"], {"bold": span["flags"] & 2, "italic": span["flags"] & 1}])
            
            semantic_items.append({
                "type": b_type,
                "bbox": b["bbox"],
                "text": "".join([s[0] for s in segments]).strip(),
                "segments": segments,
                "lines": b["lines"]
            })
            
        # Phase 2: Merging
        merged = []
        for item in semantic_items:
            if not merged: merged.append(item); continue
            prev = merged[-1]
            if prev["type"] == item["type"] and item["type"] in ["paragraph", "reference"]:
                # Logic for merging could be more complex (sentence completion check)
                prev["text"] += " " + item["text"]
                prev["segments"].extend(item["segments"])
                prev["lines"].extend(item["lines"])
                prev["bbox"] = [min(prev["bbox"][0], item["bbox"][0]), min(prev["bbox"][1], item["bbox"][1]),
                                max(prev["bbox"][2], item["bbox"][2]), max(prev["bbox"][3], item["bbox"][3])]
            else:
                merged.append(item)
        return merged

