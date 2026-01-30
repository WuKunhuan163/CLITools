#!/usr/bin/env python3
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import fitz  # PyMuPDF

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
                processed_lines.append('')
            continue
            
        current_paragraph.append(line)
        if line and line[-1] in ending_punctuations:
            processed_lines.append(' '.join(current_paragraph))
            current_paragraph = []
            processed_lines.append('')
            
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

def sort_blocks_reading_order(blocks: List[Any], page_width: float, page_height: float) -> List[Any]:
    """
    Advanced sorting for complex paper layouts.
    Handles multi-column text and correctly identifies headers/footers.
    """
    if not blocks:
        return []

    # 1. Identify headers and footers by position, regardless of width
    # Thresholds: top 10% and bottom 10%
    header_y_limit = page_height * 0.1
    footer_y_limit = page_height * 0.9
    
    headers = []
    footers = []
    body_blocks = []
    
    for b in blocks:
        x0, y0, x1, y1 = b[:4]
        if y1 < header_y_limit:
            headers.append(b)
        elif y0 > footer_y_limit:
            footers.append(b)
        else:
            body_blocks.append(b)
            
    # 2. Process body blocks into vertical zones separated by spanning elements
    body_blocks.sort(key=lambda b: b[1]) # Sort by Y
    
    spanning_width_threshold = page_width * 0.6
    
    zones = []
    current_zone = []
    
    for b in body_blocks:
        x0, y0, x1, y1 = b[:4]
        is_spanning = (x1 - x0) > spanning_width_threshold
        
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
    # Headers first
    headers.sort(key=lambda b: b[1])
    final_sorted.extend(headers)
    
    # Body zones
    for zone_type, zone_blocks in zones:
        if zone_type == 'spanning':
            final_sorted.extend(zone_blocks)
        else:
            # Body zone: Detect sub-columns using X clustering
            zone_blocks.sort(key=lambda b: b[0])
            
            columns = []
            if zone_blocks:
                current_col = [zone_blocks[0]]
                for i in range(1, len(zone_blocks)):
                    prev_b = zone_blocks[i-1]
                    curr_b = zone_blocks[i]
                    
                    # Threshold for new column: 5% of page width
                    if curr_b[0] - prev_b[0] > page_width * 0.05:
                        columns.append(sorted(current_col, key=lambda b: b[1]))
                        current_col = [curr_b]
                    else:
                        current_col.append(curr_b)
                columns.append(sorted(current_col, key=lambda b: b[1]))
                
            for col in columns:
                final_sorted.extend(col)
                
    # Footers last
    footers.sort(key=lambda b: b[1])
    final_sorted.extend(footers)
    
    return final_sorted

def extract_pdf(pdf_path: Path, output_images_dir: Path, page_spec: Optional[str] = None) -> str:
    """Extract text and images from a PDF file."""
    doc = fitz.open(str(pdf_path))
    content = []
    
    output_images_dir.mkdir(parents=True, exist_ok=True)
    
    pages = parse_page_spec(page_spec, doc.page_count)
    
    for page_num in pages:
        page = doc[page_num]
        page_rect = page.rect
        content.append(f"## Page {page_num + 1}\n")
        
        # 1. Extract Images
        image_list = page.get_images(full=True)
        if image_list:
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha >= 4:  # CMYK
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    img_bytes = pix.tobytes("png")
                    img_hash = hashlib.md5(img_bytes).hexdigest()
                    img_filename = f"img_{page_num+1}_{img_index}_{img_hash[:8]}.png"
                    img_path = output_images_dir / img_filename
                    
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                    
                    content.append(f"[placeholder: image]\n![]({img_path.absolute()})\n")
                    pix = None
                except: pass

        # 2. Extract Text with improved layout-aware sorting
        blocks = page.get_text("blocks")
        sorted_blocks = sort_blocks_reading_order(blocks, page_rect.width, page_rect.height)
        
        page_text = ""
        for b in sorted_blocks:
            if b[6] == 0: # Text block
                block_text = b[4].strip()
                if block_text:
                    processed_block = process_text_linebreaks(block_text)
                    page_text += processed_block + "\n\n"
        
        content.append(page_text)
        
    doc.close()
    return '\n'.join(content)
