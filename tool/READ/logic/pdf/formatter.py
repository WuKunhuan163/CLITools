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

def get_span_style(span: Dict[str, Any], median_size: float, line_y: float) -> Dict[str, Any]:
    """Extract style information from a span."""
    flags = span["flags"]
    size = span["size"]
    font_name = span["font"].lower()
    origin_y = span["origin"][1]
    color_int = span["color"]
    
    is_italic = flags & 2 or "italic" in font_name or "oblique" in font_name
    is_bold = flags & 16 or "bold" in font_name
    
    is_super = False
    is_sub = False
    if size < median_size * 0.95:
        if origin_y < line_y - size * 0.1: is_super = True
        elif origin_y > line_y + size * 0.1: is_sub = True
        
    hex_color = None
    if color_int != 0:
        r = (color_int >> 16) & 0xFF
        g = (color_int >> 8) & 0xFF
        b = color_int & 0xFF
        if r > 30 or g > 30 or b > 30:
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            
    return {
        "bold": is_bold,
        "italic": is_italic,
        "super": is_super,
        "sub": is_sub,
        "color": hex_color
    }

def apply_style_to_text(text: str, style: Dict[str, Any]) -> str:
    """Apply style attributes to a clean text string."""
    if not text:
        return ""
        
    res = text
    # 1. Bold/Italic
    if style["bold"] and style["italic"]: res = f"***{res}***"
    elif style["bold"]: res = f"**{res}**"
    elif style["italic"]: res = f"*{res}*"
        
    # 2. Sub/Super
    if style["super"]: res = f"<sup>{res}</sup>"
    elif style["sub"]: res = f"<sub>{res}</sub>"
    
    # 3. Color
    if style["color"]:
        res = f'<span style="color:{style["color"]}">{res}</span>'
        
    return res

def format_span(span: Dict[str, Any], median_size: float, line_y: float) -> str:
    """Legacy format_span, now uses apply_style_to_text."""
    style = get_span_style(span, median_size, line_y)
    text = span["text"]
    leading_space = " " if text.startswith(" ") else ""
    trailing_space = " " if text.endswith(" ") else ""
    return f"{leading_space}{apply_style_to_text(text.strip(), style)}{trailing_space}"

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
