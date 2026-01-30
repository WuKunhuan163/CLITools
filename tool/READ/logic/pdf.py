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

def extract_pdf(pdf_path: Path, output_images_dir: Path, page_spec: Optional[str] = None) -> str:
    """Extract text and images from a PDF file."""
    doc = fitz.open(str(pdf_path))
    content = []
    
    output_images_dir.mkdir(parents=True, exist_ok=True)
    
    pages = parse_page_spec(page_spec, doc.page_count)
    
    for page_num in pages:
        page = doc[page_num]
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

        # 2. Extract Text
        text = page.get_text()
        processed_text = process_text_linebreaks(text)
        content.append(processed_text + "\n")
        
    doc.close()
    return '\n'.join(content)
