#!/usr/bin/env python3
import hashlib
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from logic.config import get_color
from .algorithm.sorter import ReadingOrderSorter
from .algorithm.semantic import identify_block_type
from .formatter import get_span_style, apply_style_to_text, process_text_linebreaks, format_segments_with_color_merging, strip_non_standard_chars
from .layout import parse_page_spec, get_median_font_size

def is_sentence_complete(text: str) -> bool:
    """Check if a text block ends with a sentence-ending punctuation."""
    text = text.strip()
    if not text: return True
    # Standard sentence endings
    if text[-1] in {'.', '!', '?', ':', ';', '。', '！', '？', '：', '；'}:
        return True
    # Reference style endings like "[12]" or "12." at the end of a block are also "complete" in a sense
    if re.search(r'\[\d+\]$', text) or re.search(r'\d+\.$', text):
        return True
    return False

def extract_single_pdf_page(doc: fitz.Document, page_num: int, output_pages_root: Path, median_size: float, alpha_int: int = 51) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
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
    
    # Get DRAW tool interface
    try:
        from tool.DRAW.logic.interface.main import get_interface as get_draw_interface
        draw_iface = get_draw_interface()
    except ImportError:
        draw_iface = None

    # 3. Images folder inside page folder
    page_images_dir = page_dir / "images"
    page_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Define semantic mapping to colors
    semantic_color_map = {
        "title": get_color("RGBA_RED", [255, 0, 0, 100]),
        "heading": get_color("RGBA_ORANGE", [255, 165, 0, 100]),
        "paragraph": get_color("RGBA_GREEN", [0, 255, 0, 60]),
        "reference": get_color("RGBA_MAGENTA", [255, 0, 255, 100]),
        "header": get_color("RGBA_BLUE", [0, 0, 255, 100]),
        "footer": get_color("RGBA_GRAY", [128, 128, 128, 100]),
        "image": get_color("RGBA_YELLOW", [255, 255, 0, 100]),
        "table": get_color("RGBA_CYAN", [0, 255, 255, 100]),
    }

    # Data for DRAW tool
    rects_to_draw = []
    labels_to_draw = []
    legend_items = {}

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
                    color = semantic_color_map.get("image", [255, 255, 0, 100])
                    rects_to_draw.append({
                        "bbox": [bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom],
                        "fill": tuple(list(color[:3]) + [alpha_int])
                    })
                    legend_items["Image"] = tuple(list(color[:3]) + [255])
                
                pix_img = None
            except: pass

    # 5. Text
    page_dict = page.get_text("dict")
    # Instead of sorting blocks, we extract all lines and sort them.
    # This handles cases where fitz merges lines from different columns into one block.
    all_lines = []
    for b in page_dict["blocks"]:
        if b.get("type") != 0: continue
        for line in b["lines"]:
            # Add block info to line for later context if needed
            line["block_bbox"] = b["bbox"]
            all_lines.append(line)
            
    sorted_lines = ReadingOrderSorter.sort_blocks(all_lines, page_rect.width, page_rect.height)
    
    # Group sorted lines back into blocks based on proximity and style
    grouped_blocks = []
    if sorted_lines:
        current_block_lines = [sorted_lines[0]]
        for i in range(1, len(sorted_lines)):
            prev_line = sorted_lines[i-1]
            curr_line = sorted_lines[i]
            
            # Check for block break: large Y gap OR horizontal shift
            y_gap = curr_line["bbox"][1] - prev_line["bbox"][3]
            x_shift = abs(curr_line["bbox"][0] - prev_line["bbox"][0])
            
            # Also check if they were originally in different blocks and the gap is significant
            different_original_blocks = prev_line.get("block_bbox") != curr_line.get("block_bbox")
            
            if y_gap > 10 or x_shift > 50 or (different_original_blocks and y_gap > 5):
                grouped_blocks.append({"lines": current_block_lines, "bbox": [
                    min(l["bbox"][0] for l in current_block_lines),
                    min(l["bbox"][1] for l in current_block_lines),
                    max(l["bbox"][2] for l in current_block_lines),
                    max(l["bbox"][3] for l in current_block_lines)
                ]})
                current_block_lines = [curr_line]
            else:
                current_block_lines.append(curr_line)
        
        grouped_blocks.append({"lines": current_block_lines, "bbox": [
            min(l["bbox"][0] for l in current_block_lines),
            min(l["bbox"][1] for l in current_block_lines),
            max(l["bbox"][2] for l in current_block_lines),
            max(l["bbox"][3] for l in current_block_lines)
        ]})

    page_content_parts = []
    if page_images_content:
        page_content_parts.extend(page_images_content)
        
    semantic_info = []
    extracted_block_counter = 1
    
    from PIL import ImageFont
    try:
        label_font = ImageFont.truetype("Arial.ttf", int(10 * zoom))
    except:
        label_font = ImageFont.load_default()

    in_reference_section = False
    
    # Phase 1: Convert blocks to semantic items
    semantic_items = []
    for b in grouped_blocks:
        block_type = identify_block_type(b, page_rect, median_size)
        
        # State-based reference detection refinement
        if block_type == "reference":
            in_reference_section = True
        elif in_reference_section:
            if block_type in ["heading", "title", "footer", "header"]:
                in_reference_section = False
            else:
                block_type = "reference"
        
        segments = []
        for line_idx, line in enumerate(b["lines"]):
            if not line["spans"]: continue
            line_y = line["spans"][0]["origin"][1]
            if segments and not segments[-1][0].endswith(" "):
                segments[-1][0] += " "
            for span in line["spans"]:
                style = get_span_style(span, median_size, line_y)
                text = strip_non_standard_chars(span["text"])
                if not text: continue
                
                if not segments: segments.append([text, style])
                else:
                    prev_text, prev_style = segments[-1]
                    if style == prev_style: segments[-1][0] += text
                    else: segments.append([text, style])
        
        if not segments: continue
        
        block_text_raw = "".join([s[0] for s in segments]).strip()
        if not block_text_raw: continue
        
        semantic_items.append({
            "type": block_type,
            "bbox": list(b["bbox"]),
            "segments": segments,
            "text": block_text_raw
        })

    # Phase 2: Merging logical blocks
    merged_items = []
    for item in semantic_items:
        if not merged_items:
            merged_items.append(item)
            continue
        
        prev = merged_items[-1]
        should_merge = False
        
        # Merge broken paragraphs
        if prev["type"] == "paragraph" and item["type"] == "paragraph":
            if not is_sentence_complete(prev["text"]):
                # print(f"DEBUG: Merging paragraphs: '{prev['text'][-20:]}' and '{item['text'][:20]}'")
                should_merge = True
        
        # Merge consecutive references
        if prev["type"] == "reference" and item["type"] == "reference":
            should_merge = True
            
        if should_merge:
            # Merge segments
            if prev["segments"][-1][0].endswith(" ") or item["segments"][0][0].startswith(" "):
                pass # Already has space
            else:
                prev["segments"][-1][0] += " "
                
            # Try to merge last segment of prev with first of item if styles match
            if prev["segments"][-1][1] == item["segments"][0][1]:
                prev["segments"][-1][0] += item["segments"][0][0]
                prev["segments"].extend(item["segments"][1:])
            else:
                prev["segments"].extend(item["segments"])
            
            prev["text"] = (prev["text"] + " " + item["text"]).strip()
            # Envelop bbox
            prev["bbox"] = [
                min(prev["bbox"][0], item["bbox"][0]),
                min(prev["bbox"][1], item["bbox"][1]),
                max(prev["bbox"][2], item["bbox"][2]),
                max(prev["bbox"][3], item["bbox"][3])
            ]
        else:
            merged_items.append(item)

    # Phase 3: Final formatting and visualization
    for item in merged_items:
        block_type = item["type"]
        bbox = item["bbox"]
        segments = item["segments"]
        block_text_raw = item["text"]
        
        color = semantic_color_map.get(block_type, [0, 255, 0, 60])
        fill_color = tuple(list(color[:3]) + [alpha_int])
        
        rects_to_draw.append({
            "bbox": [bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom],
            "fill": fill_color
        })
        
        type_label = block_type.capitalize()
        if type_label not in legend_items:
            legend_items[type_label] = tuple(list(color[:3]) + [255])
        
        block_id_num = extracted_block_counter
        block_id = f"b{block_id_num:03d}"
        extracted_block_counter += 1
        
        # Label with ID in top-left
        labels_to_draw.append({
            "pos": (bbox[0]*zoom + 2, bbox[1]*zoom + 2), # Use merged bbox for label position
            "text": str(block_id_num),
            "font": label_font,
            "bg_color": (255, 255, 255, 255),
            "border_color": (0, 0, 0, 255)
        })

        semantic_info.append({
            "id": block_id,
            "type": block_type,
            "bbox": bbox,
            "text_preview": block_text_raw[:50] + "..." if len(block_text_raw) > 50 else block_text_raw
        })
        
        block_md = f"<!-- block_id: {block_id} type: {block_type} -->\n"
        
        # Special logic for headings and references
        if block_type in ["paragraph", "heading"]:
            # Check for bold heading at start
            first_is_bold = segments[0][1]["bold"]
            if first_is_bold:
                bold_end_idx = -1
                for i in range(1, len(segments)):
                    if not segments[i][1]["bold"]:
                        bold_end_idx = i
                        break
                
                if bold_end_idx != -1:
                    bold_text = "".join([s[0] for s in segments[:bold_end_idx]]).strip()
                    # Heuristic for heading: short or starts with numbering
                    if len(bold_text.split()) < 12 or re.match(r"^\d+(\.\d+)*\s", bold_text):
                        heading_md = format_segments_with_color_merging(segments[:bold_end_idx])
                        body_md = format_segments_with_color_merging(segments[bold_end_idx:])
                        block_md += heading_md.strip() + " \n\n " + body_md.lstrip() # Added spaces for regex match safety
                    else:
                        block_md += format_segments_with_color_merging(segments)
                else:
                    # Entire block is bold, maybe it IS a heading?
                    if len(block_text_raw.split()) < 12 or re.match(r"^\d+(\.\d+)*\s", block_text_raw):
                         block_md += format_segments_with_color_merging(segments) + "\n\n"
                    else:
                         block_md += format_segments_with_color_merging(segments)
            else:
                block_md += format_segments_with_color_merging(segments)
                
        elif block_type == "reference":
            # Re-format merged references
            raw_content = format_segments_with_color_merging(segments)
            # Split by numbering: " 1. ", " [1] ", etc.
            ref_parts = re.split(r'(\s+(?:\[\d+\]|\d+\.)\s+)', raw_content)
            if len(ref_parts) > 1:
                # Keep first part (e.g. "References")
                formatted = ref_parts[0].strip()
                for i in range(1, len(ref_parts), 2):
                    num = ref_parts[i].strip()
                    text = ref_parts[i+1].strip() if i+1 < len(ref_parts) else ""
                    formatted += "\n\n" + num + " " + text
                block_md += formatted
            else:
                block_md += raw_content
        else:
            block_md += format_segments_with_color_merging(segments)
            
        block_md = re.sub(r' +', ' ', block_md)
        if block_md.strip():
            page_content_parts.append(block_md.strip())
                
    content = "\n\n".join(page_content_parts)
    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    # Perform drawing using DRAW tool if available
    if draw_iface:
        vis_img = draw_iface["draw_rects_with_alpha"](vis_img, rects_to_draw)
        vis_img = draw_iface["draw_labels"](vis_img, labels_to_draw)
        vis_img = draw_iface["append_legend"](vis_img, legend_items)
    else:
        # Fallback
        draw = ImageDraw.Draw(vis_img)
        for r in rects_to_draw:
            draw.rectangle(r["bbox"], fill=r["fill"])
        for l in labels_to_draw:
            draw.text(l["pos"], l["text"], fill=(0,0,0,255), font=l["font"])

    vis_img.save(page_dir / "extracted.png")
    
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
        content, images, semantic = extract_single_pdf_page(doc, page_num, pages_dir, median_size, 51)
        extracted_pages.append({
            "page_num": page_num + 1,
            "content": content,
            "images": images,
            "semantic": semantic
        })
    doc.close()
    return extracted_pages
