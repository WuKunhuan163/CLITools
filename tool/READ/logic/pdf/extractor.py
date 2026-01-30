#!/usr/bin/env python3
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from .layout import ReadingOrderSorter
from .formatter import get_span_style, apply_style_to_text, process_text_linebreaks, get_median_font_size

def parse_page_spec(spec: str, total_pages: int) -> List[int]:
    """Parse page specification like '1,3,5-7'."""
    pages = []
    if not spec:
        return list(range(total_pages))
        
    for part in spec.split(','):
        part = part.strip()
        if not part: continue
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

def extract_single_pdf_page(doc: fitz.Document, page_num: int, output_images_root: Path, median_size: float, md_file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extract a single PDF page (0-indexed).
    Returns (markdown_content, image_metadata_list)
    """
    page = doc[page_num]
    page_rect = page.rect
    actual_page_num = page_num + 1
    
    # Per-page images folder
    page_images_dir = output_images_root / f"page_{actual_page_num:03d}"
    page_images_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Images
    image_list = page.get_images(full=True)
    page_images_content = []
    image_metadata = []
    
    if image_list:
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                img_bytes = pix.tobytes("png")
                
                # Image filename without hash as requested
                img_filename = f"image_{img_index + 1:03d}.png"
                img_path = page_images_dir / img_filename
                
                with open(img_path, "wb") as f: f.write(img_bytes)
                
                # Relative path for Markdown preview
                rel_img_path = os.path.relpath(img_path, md_file_path.parent)
                page_images_content.append(f"![]({rel_img_path})\n")
                
                # Metadata for info.json
                image_metadata.append({
                    "page": actual_page_num,
                    "index": img_index + 1,
                    "filename": img_filename,
                    "rel_path": rel_img_path,
                    "abs_path": str(img_path.resolve()),
                    "type": "unknown" # To be identified by vision API if needed
                })
                pix = None
            except: pass

    # 2. Text
    page_dict = page.get_text("dict")
    blocks = page_dict["blocks"]
    sorted_blocks = ReadingOrderSorter.sort_blocks(blocks, page_rect.width, page_rect.height)
    
    page_content_parts = []
    if page_images_content:
        page_content_parts.extend(page_images_content)
        
    for b in sorted_blocks:
        if b.get("type") != 0: continue
        
        segments = []
        for line_idx, line in enumerate(b["lines"]):
            if not line["spans"]: continue
            
            line_y = line["spans"][0]["origin"][1]
            if segments and not segments[-1][0].endswith(" "):
                segments.append([" ", segments[-1][1]])
                
            for span in line["spans"]:
                style = get_span_style(span, median_size, line_y)
                text = span["text"]
                if not segments:
                    segments.append([text, style])
                else:
                    prev_text, prev_style = segments[-1]
                    if style == prev_style:
                        segments[-1][0] += text
                    else:
                        segments.append([text, style])
        
        if not segments: continue
        
        block_md = ""
        for text, style in segments:
            leading_space = " " if text.startswith(" ") else ""
            trailing_space = " " if text.endswith(" ") else ""
            formatted = apply_style_to_text(text.strip(), style)
            block_md += f"{leading_space}{formatted}{trailing_space}"
            
        import re
        block_md = re.sub(r' +', ' ', block_md)
        if block_md.strip():
            page_content_parts.append(block_md.strip())
                
    return "\n\n".join(page_content_parts), image_metadata

def extract_pdf_pages(pdf_path: Path, output_images_dir: Path, page_spec: Optional[str] = None) -> List[Dict[str, Any]]:
    doc = fitz.open(str(pdf_path))
    extracted_pages = []
    pages = parse_page_spec(page_spec, doc.page_count)
    all_blocks = []
    for p_num in pages:
        all_blocks.extend(doc[p_num].get_text("dict")["blocks"])
    median_size = get_median_font_size(all_blocks)
    dummy_md_path = Path("result/pages/page_001.md")
    for page_num in pages:
        content, _ = extract_single_pdf_page(doc, page_num, output_images_dir, median_size, dummy_md_path)
        extracted_pages.append({
            "page_num": page_num + 1,
            "content": content
        })
    doc.close()
    return extracted_pages
