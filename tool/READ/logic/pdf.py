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

def sort_blocks_by_reading_order(blocks: List[Any], page_width: float) -> List[Any]:
    """Sort text blocks into a logical reading order (multi-column aware)."""
    # Simple heuristic: Split into 2 columns if width allows
    # Blocks: (x0, y0, x1, y1, "text", block_no, block_type)
    
    # Sort primarily by X-halves, then by top Y
    def get_sort_key(b):
        x0, y0, x1, y1 = b[:4]
        # Identify which column it belongs to (0 or 1)
        # Using a threshold of 0.5 * page_width
        column = 0 if x0 < page_width * 0.5 else 1
        # If block spans more than 60% of the page, it's likely a header/footer or full-width
        if (x1 - x0) > page_width * 0.6:
            # Full width blocks: 
            # If at the top, they should come first (column -1?)
            # If at the bottom, they should come last (column 2?)
            if y0 < page_width * 0.2: column = -1 # Top header
            elif y1 > page_width * 0.8: column = 2 # Bottom footer
            else: column = 0 # Assume left for now
            
        return (column, y0)

    return sorted(blocks, key=get_sort_key)

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

        # 2. Extract Text with layout-aware sorting
        # get_text("blocks") returns List of (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks")
        sorted_blocks = sort_blocks_by_reading_order(blocks, page_rect.width)
        
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
