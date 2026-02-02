from typing import Any, Dict, List
import re

def identify_block_type(block: Dict[str, Any], page_rect: Any, median_font_size: float) -> str:
    """
    Identifies the semantic type of a text block based on heuristics.
    """
    bbox = block["bbox"]
    block_text_raw = "".join([s["text"] for l in block["lines"] for s in l["spans"]]).strip()
    
    if not block_text_raw:
        return "unknown"

    max_font_in_block = 0
    if block["lines"]:
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip():
                    max_font_in_block = max(max_font_in_block, span["size"])

    # Heuristics for semantic type
    # 1. Headers/Footers (position-based, with content check)
    if bbox[1] < page_rect.height * 0.05: # Top 5%
        # Check if it's a short, isolated line
        if len(block_text_raw.split()) < 15 and (bbox[2] - bbox[0]) < page_rect.width * 0.6:
            return "header"
            
    if bbox[3] > page_rect.height * 0.95: # Bottom 5%
        # Check if it's a short, isolated line (e.g., page numbers, document info)
        if len(block_text_raw.split()) < 20: 
            return "footer"

    # 2. Titles (very large font, often centered)
    if max_font_in_block > median_font_size * 1.8: # Significantly larger
        return "title"

    # 3. Headings (larger font, often bold)
    if max_font_in_block > median_font_size * 1.2: # Moderately larger
        # Check if it's bold and starts with a number or common heading pattern
        first_span_bold = False
        if block["lines"] and block["lines"][0]["spans"]:
            first_span = block["lines"][0]["spans"][0]
            if first_span["flags"] & 16 or "bold" in first_span["font"].lower():
                first_span_bold = True

        if first_span_bold and (re.match(r"^\d+(\.\d+)*\s", block_text_raw) or block_text_raw.isupper()):
            return "heading"
        elif "conclusion" in block_text_raw.lower() or "discussion" in block_text_raw.lower() or "acknowledgments" in block_text_raw.lower():
            return "heading"
        else:
            return "heading" # Fallback for large font if not header/footer

    # 4. DOI (specific patterns)
    if re.search(r"doi:", block_text_raw, re.IGNORECASE) or re.match(r"^10\.\d{4,9}/", block_text_raw):
        return "doi"

    # 5. References (specific patterns)
    # Refine to avoid matching headings like "7. CONCLUSION"
    if re.match(r"^References", block_text_raw, re.IGNORECASE):
        return "reference"
    elif re.match(r"^\[\d+\]", block_text_raw):
        return "reference"
    elif (re.match(r"^\d+\.\s", block_text_raw) and len(block_text_raw) > 30 and not any(h in block_text_raw.upper() for h in ["CONCLUSION", "ABSTRACT", "INTRODUCTION", "DISCUSSION"])):
        # Added length check and excluded common headings
        return "reference"
    elif "arXiv:" in block_text_raw:
        return "reference"

    # Default to paragraph
    return "paragraph"

