#!/usr/bin/env python3
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from logic.config import get_color
from .layout import ReadingOrderSorter
from .formatter import get_span_style, apply_style_to_text, process_text_linebreaks, get_median_font_size, format_segments_with_color_merging

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

def extract_single_pdf_page(doc: fitz.Document, page_num: int, output_pages_root: Path, median_size: float) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extract a single PDF page (0-indexed).
    Returns (markdown_content, image_metadata_list, semantic_info_list)
    """
    page = doc[page_num]
    page_rect = page.rect
    actual_page_num = page_num + 1
    
    # Per-page folder
    page_dir = output_pages_root / f"page_{actual_page_num:03d}"
    page_dir.mkdir(parents=True, exist_ok=True)
    
    # Path for the markdown file
    md_file_path = page_dir / "extracted.md"
    
    # 1. Save source.pdf (single page)
    source_pdf_path = page_dir / "source.pdf"
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    new_doc.save(str(source_pdf_path))
    new_doc.close()
    
    # 2. Save source.png (screenshot) - 2x resolution
    source_png_path = page_dir / "source.png"
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(source_png_path))
    
    # Prepare for visualization with true alpha transparency
    vis_img = Image.open(source_png_path).convert("RGBA")
    # Create a separate layer for semantic blocks to enable true alpha blending
    overlay = Image.new("RGBA", vis_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # 3. Images folder inside page folder
    page_images_dir = page_dir / "images"
    page_images_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. Extract Images
    image_list = page.get_images(full=True)
    page_images_content = []
    image_metadata = []
    
    if image_list:
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                pix_img = fitz.Pixmap(doc, xref)
                if pix_img.n - pix_img.alpha >= 4: pix_img = fitz.Pixmap(fitz.csRGB, pix_img)
                img_bytes = pix_img.tobytes("png")
                
                img_filename = f"image_{img_index + 1:03d}.png"
                img_path = page_images_dir / img_filename
                
                with open(img_path, "wb") as f: f.write(img_bytes)
                
                # Relative path for Markdown preview
                rel_img_path = os.path.relpath(img_path, page_dir)
                page_images_content.append(f"![]({rel_img_path})\n")
                
                # Metadata for info.json
                image_metadata.append({
                    "page": actual_page_num,
                    "index": img_index + 1,
                    "filename": img_filename,
                    "rel_path": rel_img_path,
                    "abs_path": str(img_path.resolve()),
                    "type": "unknown"
                })
                
                # Visualize image region
                img_info = page.get_image_info(xref=xref)
                if img_info:
                    bbox = img_info[0]["bbox"]
                    color = get_color("SEMANTIC_IMAGE", [255, 255, 0, 100])
                    draw.rectangle([bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom], fill=tuple(color))
                
                pix_img = None
            except: pass

    # 5. Text
    page_dict = page.get_text("dict")
    blocks = page_dict["blocks"]
    sorted_blocks = ReadingOrderSorter.sort_blocks(blocks, page_rect.width, page_rect.height)
    
    page_content_parts = []
    if page_images_content:
        page_content_parts.extend(page_images_content)
        
    semantic_info = []
    extracted_block_counter = 1
    
    for b in sorted_blocks:
        if b.get("type") != 0: continue
        
        # Determine semantic type
        block_type = "paragraph"
        bbox = b["bbox"]
        
        # Heuristics for semantic type
        block_text_raw = "".join([s["text"] for l in b["lines"] for s in l["spans"]]).strip()
        if not block_text_raw: continue
        
        # Check if it's a title (large font, centered-ish)
        max_font_in_block = max([s["size"] for l in b["lines"] for s in l["spans"]])
        
        # Determine semantic type
        if max_font_in_block > median_size * 1.5:
            block_type = "title"
        elif bbox[1] < page_rect.height * 0.08:
            block_type = "header"
        elif bbox[3] > page_rect.height * 0.92:
            block_type = "footer"
        elif max_font_in_block > median_size * 1.1:
            block_type = "heading" # Subtitles/Sections
        else:
            block_type = "paragraph"
            
        color_key = f"SEMANTIC_{block_type.upper()}"
        color = get_color(color_key, [0, 255, 0, 60])
        # Use 20% alpha (approx 51)
        color = list(color[:3]) + [51]
        
        # Draw semi-transparent rectangle
        draw.rectangle([bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom], fill=tuple(color))
        
        block_id_num = extracted_block_counter
        block_id = f"b{block_id_num:03d}"
        extracted_block_counter += 1
        
        # Label with ID in top-left
        try:
            from PIL import ImageFont
            try:
                font = ImageFont.truetype("Arial.ttf", int(10 * zoom))
            except:
                font = ImageFont.load_default()
            draw.text((bbox[0]*zoom + 2, bbox[1]*zoom + 2), str(block_id_num), fill=(0,0,0,255), font=font)
        except: pass

        semantic_info.append({
            "id": block_id,
            "type": block_type,
            "bbox": bbox,
            "text_preview": block_text_raw[:50] + "..." if len(block_text_raw) > 50 else block_text_raw
        })
        
        segments = []
        for line_idx, line in enumerate(b["lines"]):
            if not line["spans"]: continue
            line_y = line["spans"][0]["origin"][1]
            if segments and not segments[-1][0].endswith(" "):
                segments[-1][0] += " "
            for span in line["spans"]:
                style = get_span_style(span, median_size, line_y)
                text = span["text"]
                if not segments: segments.append([text, style])
                else:
                    prev_text, prev_style = segments[-1]
                    if style == prev_style: segments[-1][0] += text
                    else: segments.append([text, style])
        
        if not segments: continue
        
        block_md = f"<!-- block_id: {block_id} type: {block_type} -->\n"
        block_md += format_segments_with_color_merging(segments)
            
        import re
        block_md = re.sub(r' +', ' ', block_md)
        if block_md.strip():
            page_content_parts.append(block_md.strip())
                
    content = "\n\n".join(page_content_parts)
    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    # Composite the overlay onto the original image for true transparency
    final_vis = Image.alpha_composite(vis_img, overlay)
    final_vis.save(page_dir / "extracted.png")
    
    return content, image_metadata, semantic_info

def extract_pdf_pages(pdf_path: Path, output_root: Path, page_spec: Optional[str] = None) -> List[Dict[str, Any]]:
    doc = fitz.open(str(pdf_path))
    extracted_pages = []
    pages = parse_page_spec(page_spec, doc.page_count)
    
    # Get median font size across all target pages
    all_blocks = []
    for p_num in pages:
        all_blocks.extend(doc[p_num].get_text("dict")["blocks"])
    median_size = get_median_font_size(all_blocks)
    
    pages_dir = output_root / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    
    for page_num in pages:
        content, images, semantic = extract_single_pdf_page(doc, page_num, pages_dir, median_size)
        extracted_pages.append({
            "page_num": page_num + 1,
            "content": content,
            "images": images,
            "semantic": semantic
        })
    doc.close()
    return extracted_pages
