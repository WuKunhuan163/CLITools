#!/usr/bin/env python3
from typing import List, Dict, Any

def process_text_linebreaks(text: str) -> str:
    """Smartly merge lines to avoid fragmented sentences."""
    if not text.strip():
        return text
    
    ending_punctuations = {'.', '!', '?', ':', ';', '。', '！', '？', '：', '；'}
    lines = text.split('\n')
    processed_lines = []
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_paragraph:
                processed_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            continue
            
        current_paragraph.append(line)
        if line and line[-1] in ending_punctuations:
            processed_lines.append(' '.join(current_paragraph))
            current_paragraph = []
            
    if current_paragraph:
        processed_lines.append(' '.join(current_paragraph))
        
    return '\n'.join(processed_lines)

def format_span(span: Dict[str, Any], median_size: float, line_y: float) -> str:
    """Format a text span with Markdown (bold, italic, sub/sup)."""
    text = span["text"]
    if not text.strip():
        return text
        
    flags = span["flags"]
    size = span["size"]
    font_name = span["font"].lower()
    origin_y = span["origin"][1]
    
    is_italic = flags & 2 or "italic" in font_name or "oblique" in font_name
    is_bold = flags & 16 or "bold" in font_name
    
    # Sub/Super Detection
    is_super = False
    is_sub = False
    if size < median_size * 0.95:
        if origin_y < line_y - size * 0.1: is_super = True
        elif origin_y > line_y + size * 0.1: is_sub = True
            
    leading_space = " " if text.startswith(" ") else ""
    trailing_space = " " if text.endswith(" ") else ""
    clean_text = text.strip()
    
    if is_bold and is_italic: clean_text = f"***{clean_text}***"
    elif is_bold: clean_text = f"**{clean_text}**"
    elif is_italic: clean_text = f"*{clean_text}*"
        
    if is_super: clean_text = f"<sup>{clean_text}</sup>"
    elif is_sub: clean_text = f"<sub>{clean_text}</sub>"
        
    return f"{leading_space}{clean_text}{trailing_space}"

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

