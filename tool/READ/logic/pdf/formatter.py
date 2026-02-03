#!/usr/bin/env python3
from typing import List, Dict, Any, Tuple
import re

def strip_non_standard_chars(text: str) -> str:
    """Remove non-printable or non-standard characters."""
    if not text:
        return ""
    # Keep standard printable characters, tabs, and newlines
    # Avoid \b (backspace), \r, etc.
    # [^\x20-\x7E\s] matches non-ASCII printable chars, but we want to keep some Unicode
    # Let's just remove control characters except \n and \t
    return "".join(c for c in text if ord(c) >= 32 or c in '\n\t')

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
        
        # Keep all colors, but clear near-black (e.g. #231f20)
        # Luminance-based or simple threshold? Simple threshold for each component is fine.
        if r < 40 and g < 40 and b < 40:
            hex_color = None
        else:
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            
    return {
        "bold": is_bold,
        "italic": is_italic,
        "super": is_super,
        "sub": is_sub,
        "color": hex_color
    }

def apply_inner_style(text: str, style: Dict[str, Any]) -> str:
    """Apply bold, italic, super, sub styles."""
    res = text
    if style["bold"] and style["italic"]: res = f"***{res}***"
    elif style["bold"]: res = f"**{res}**"
    elif style["italic"]: res = f"*{res}*"
        
    if style["super"]: res = f"<sup>{res}</sup>"
    elif style["sub"]: res = f"<sub>{res}</sub>"
    return res

def apply_style_to_text(text: str, style: Dict[str, Any]) -> str:
    """Apply all style attributes to a clean text string."""
    if not text: return ""
    
    # Extract leading/trailing spaces
    stripped = text.lstrip()
    leading_spaces = text[:len(text) - len(stripped)]
    text = stripped
    
    stripped = text.rstrip()
    trailing_spaces = text[len(stripped):]
    text = stripped
    
    if not text: return leading_spaces + trailing_spaces

    res = apply_inner_style(text, style)
    
    if style["color"]:
        res = f'<span style="color:{style["color"]}">{res}</span>'
        
    return leading_spaces + res + trailing_spaces

def format_segments_with_color_merging(segments: List[Tuple[str, Dict[str, Any]]]) -> str:
    """Merge segments with the same color into a single span."""
    if not segments: return ""
    
    output_parts = []
    current_color_group = []
    current_color = None
    
    for text, style in segments:
        color = style["color"]
        if color == current_color:
            current_color_group.append((text, style))
        else:
            if current_color_group:
                output_parts.append(wrap_color_group(current_color_group, current_color))
            current_color = color
            current_color_group = [(text, style)]
            
    if current_color_group:
        output_parts.append(wrap_color_group(current_color_group, current_color))
        
    return "".join(output_parts)

def wrap_color_group(group: List[Tuple[str, Dict[str, Any]]], color: str) -> str:
    """Wrap a group of segments in a single color span if color exists."""
    inner_content = "".join([apply_inner_style(t, s) for t, s in group])
    if color:
        return f'<span style="color:{color}">{inner_content}</span>'
    return inner_content

def merge_spans(spans: List[Dict[str, Any]], median_size: float, line_y: float) -> str:
    """Merge adjacent spans with identical styles into a single string."""
    if not spans:
        return ""
    
    merged_parts = []
    current_text = ""
    current_style = None
    
    for span in spans:
        style = get_span_style(span, median_size, line_y)
        
        if current_style is None:
            current_style = style
            current_text = span["text"]
        elif style == current_style:
            current_text += span["text"]
        else:
            # Apply style to accumulated text and start new group
            merged_parts.append(apply_style_to_text(current_text, current_style))
            current_style = style
            current_text = span["text"]
            
    if current_text:
        merged_parts.append(apply_style_to_text(current_text, current_style))
        
    return "".join(merged_parts)

def format_span(span: Dict[str, Any], median_size: float, line_y: float) -> str:
    """Legacy format_span, now uses apply_style_to_text."""
    style = get_span_style(span, median_size, line_y)
    text = span["text"]
    leading_space = " " if text.startswith(" ") else ""
    trailing_space = " " if text.endswith(" ") else ""
    return f"{leading_space}{apply_style_to_text(text.strip(), style)}{trailing_space}"

def is_sentence_complete(text: str) -> bool:
    """Check if a text block ends with a sentence-ending punctuation."""
    text = text.strip()
    if not text: return True
    # Standard sentence endings
    if text[-1] in {'.', '!', '?', ':', ';', '。', '！', '？', '：', '；'}:
        # Check if it's like "et al." or "Fig." which are NOT sentence endings
        if text.endswith("et al.") or text.endswith("Fig.") or text.endswith("i.e.") or text.endswith("e.g."):
            return False
        return True
    # Reference style endings like "[12]" or "12." at the end of a block are also "complete" in a sense
    if re.search(r'\[\d+\]$', text) or re.search(r'\d+\.$', text):
        return True
    return False
