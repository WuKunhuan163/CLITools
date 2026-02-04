import re
from typing import List, Dict, Any, Tuple
from tool.READ.logic.pdf.formatter import get_span_style, strip_non_standard_chars, is_sentence_complete

def identify_block_type(block: Dict[str, Any], page_rect: Any, median_size: float) -> str:
    """
    Identifies the semantic type of a block (title, heading, paragraph, etc.)
    """
    bbox = block["bbox"]
    text = "".join([s["text"] for line in block["lines"] for s in line["spans"]]).strip()
    
    # 1. Image detection (already handled by ImageIdentifier, but safety check)
    if block.get("is_image"): return "image"
    
    # 2. Header/Footer detection
    # Top/Bottom 5% of the page (stricter than 10%)
    margin = page_rect.height * 0.05
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
    if re.match(r'^(?:\[\d+\]|\d+\.)', text) or text.lower() == "references":
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
        # Phase 1: Initial Tagging and Segment Extraction
        semantic_items = []
        in_reference_section = False
        
        for b in grouped_blocks:
            b_type = identify_block_type(b, self.page_rect, self.median_size)
            
            # State-based refinement for references
            if b_type == "reference":
                in_reference_section = True
            elif in_reference_section:
                if b_type in ["heading", "title", "footer", "header"]:
                    in_reference_section = False
                else:
                    b_type = "reference"
            
            segments = []
            for line in b["lines"]:
                if not line["spans"]: continue
                line_y = line["spans"][0]["origin"][1]
                
                for span in line["spans"]:
                    style = get_span_style(span, self.median_size, line_y)
                    text = strip_non_standard_chars(span["text"])
                    if not text: continue
                    
                    if not segments:
                        segments.append([text, style])
                    else:
                        prev_text, prev_style = segments[-1]
                        if style == prev_style:
                            segments[-1][0] += text
                        else:
                            segments.append([text, style])
            
            if not segments: continue
            block_text = "".join([s[0] for s in segments]).strip()
            if not block_text: continue
            
            semantic_items.append({
                "type": b_type,
                "bbox": list(b["bbox"]),
                "segments": segments,
                "text": block_text,
                "lines": b["lines"]
            })
            
        # Phase 2: Merging logical blocks
        merged = []
        for item in semantic_items:
            if not merged:
                merged.append(item)
                continue
            
            prev = merged[-1]
            should_merge = False
            
            if prev["type"] == item["type"] and item["type"] in ["paragraph", "reference"]:
                if not is_sentence_complete(prev["text"]):
                    should_merge = True
            
            if prev["type"] == "reference" and item["type"] == "reference":
                should_merge = True
                
            if should_merge:
                if prev["segments"][-1][1] == item["segments"][0][1]:
                    prev["segments"][-1][0] += item["segments"][0][0]
                    prev["segments"].extend(item["segments"][1:])
                else:
                    prev["segments"].extend(item["segments"])
                
                prev["text"] = (prev["text"] + " " + item["text"]).strip()
                prev["lines"].extend(item["lines"])
                prev["bbox"] = [
                    min(prev["bbox"][0], item["bbox"][0]),
                    min(prev["bbox"][1], item["bbox"][1]),
                    max(prev["bbox"][2], item["bbox"][2]),
                    max(prev["bbox"][3], item["bbox"][3])
                ]
            else:
                merged.append(item)
        
        return merged
