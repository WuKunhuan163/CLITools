#!/usr/bin/env python3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from .layout import ReadingOrderSorter
from .formatter import format_span, process_text_linebreaks, get_median_font_size

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

def extract_pdf_pages(pdf_path: Path, output_images_dir: Path, page_spec: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract text and images from a PDF file.
    Returns a list of dictionaries, one per page:
    {"page_num": int, "content": str}
    """
    doc = fitz.open(str(pdf_path))
    extracted_pages = []
    
    output_images_dir.mkdir(parents=True, exist_ok=True)
    pages = parse_page_spec(page_spec, doc.page_count)
    print(f"DEBUG: Processing pages: {pages}")
    
    for page_num in pages:
        print(f"DEBUG: Extracting page {page_num + 1}")
        page = doc[page_num]
        page_rect = page.rect
        
        # 1. Images
        image_list = page.get_images(full=True)
        page_images_content = []
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
                    page_images_content.append(f"[placeholder: image]\n![]({img_path.absolute()})\n")
                    pix = None
                except: pass

        # 2. Text
        page_dict = page.get_text("dict")
        blocks = page_dict["blocks"]
        median_size = get_median_font_size(blocks)
        sorted_blocks = ReadingOrderSorter.sort_blocks(blocks, page_rect.width, page_rect.height)
        
        page_content_parts = []
        # Add images at the top of the page if any
        if page_images_content:
            page_content_parts.extend(page_images_content)
            
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
        
        extracted_pages.append({
            "page_num": page_num + 1,
            "content": "\n\n".join(page_content_parts)
        })
        
    doc.close()
    return extracted_pages

