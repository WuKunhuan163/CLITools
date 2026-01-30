#!/usr/bin/env python3
import hashlib
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import fitz  # PyMuPDF

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
            # block structure from get_text("dict"): dict with "bbox"
            bbox = b["bbox"]
            x0, y0, x1, y1 = bbox
                
            if y1 < header_y_limit:
                headers.append(b)
            elif y0 > footer_y_limit:
                footers.append(b)
            else:
                body_blocks.append(b)
                
        # 2. Zone-based segmentation for body
        # Sort blocks by Y initially
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
                        # 5% page width threshold for new column
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

def parse_page_spec(spec: str, total_pages: int) -> List[int]:
    """Parse page specification like '1,3,5-7'."""
    pages = []
    if not spec:
        return list(range(total_pages))
        
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                pages.extend(range(max(0, start - 1), min(total_pages, end)))
            except: pass
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    pages.append(p - 1)
            except: pass
    return sorted(list(set(pages)))

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

def extract_pdf(pdf_path: Path, output_images_dir: Path, page_spec: Optional[str] = None) -> str:
    """Extract text and images with full font and layout awareness."""
    doc = fitz.open(str(pdf_path))
    content = []
    
    output_images_dir.mkdir(parents=True, exist_ok=True)
    pages = parse_page_spec(page_spec, doc.page_count)
    
    for page_num in pages:
        page = doc[page_num]
        page_rect = page.rect
        content.append(f"## Page {page_num + 1}\n")
        
        # 1. Images
        image_list = page.get_images(full=True)
        if image_list:
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                    img_bytes = pix.tobytes("png")
                    img_hash = hashlib.md5(img_bytes).hexdigest()
                    img_filename = f"img_{page_num+1}_{img_index}_{img_hash[:8]}.png"
                    img_path = output_images_dir / img_filename
                    with open(img_path, "wb") as f: f.write(img_bytes)
                    content.append(f"[placeholder: image]\n![]({img_path.absolute()})\n")
                    pix = None
                except: pass

        # 2. Text
        page_dict = page.get_text("dict")
        blocks = page_dict["blocks"]
        median_size = get_median_font_size(blocks)
        sorted_blocks = ReadingOrderSorter.sort_blocks(blocks, page_rect.width, page_rect.height)
        
        page_content_parts = []
        for b in sorted_blocks:
            if b.get("type") != 0: continue
            
            block_text_parts = []
            for line in b["lines"]:
                line_y = line["origin"][1]
                line_text = ""
                for span in line["spans"]:
                    line_text += format_span(span, median_size, line_y)
                
                if line_text.strip():
                    block_text_parts.append(line_text.strip())
            
            if block_text_parts:
                block_raw_text = "\n".join(block_text_parts)
                processed_block = process_text_linebreaks(block_raw_text)
                if processed_block.strip():
                    page_content_parts.append(processed_block.strip())
        
        content.append("\n\n".join(page_content_parts) + "\n")
        
    doc.close()
    return '\n'.join(content)
