#!/usr/bin/env python3
import hashlib
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from logic.config import get_color
from .algorithm.semantic import identify_block_type
from .formatter import get_span_style, apply_style_to_text, process_text_linebreaks, format_segments_with_color_merging, strip_non_standard_chars, is_sentence_complete
from .layout import parse_page_spec, get_median_font_size

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
        "doi": get_color("RGBA_PURPLE", [128, 0, 128, 100]),
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

    # 5. Text Extraction using LayoutEngine
    page_dict = page.get_text("dict")
    all_spans = []
    for b in page_dict["blocks"]:
        if b.get("type") != 0: continue
        for line in b["lines"]:
            for span in line["spans"]:
                # Treat each span as a "token" unit
                all_spans.append({
                    "text": span["text"],
                    "bbox": list(span["bbox"]),
                    "font": span["font"],
                    "size": span["size"],
                    "color": span["color"],
                    "flags": span["flags"],
                    "origin": list(span["origin"])
                })

    from .algorithm.layout_engine import LayoutEngine
    engine = LayoutEngine(page_rect.width, page_rect.height)
    grouped_blocks = engine.segment_tokens(all_spans)

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
        # Calculate max font size in this block for merging heuristics
        max_font_in_block = 0
        for line in b["lines"]:
            for span in line["spans"]:
                if span.get("text", "").strip():
                    max_font_in_block = max(max_font_in_block, span.get("size", 0))

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
            "text": block_text_raw,
            "lines": b["lines"],
            "max_font": max_font_in_block # Added font info for merging
        })

    # Phase 2: Merging logical blocks
    merged_items = []
    for item in semantic_items:
        if not merged_items:
            merged_items.append(item)
            continue
        
        prev = merged_items[-1]
        should_merge = False
        
        if prev["type"] == "paragraph" and item["type"] == "paragraph":
            if not is_sentence_complete(prev["text"]):
                should_merge = True
        
        if prev["type"] == "title" and item["type"] == "title":
            # Merge titles if font size is roughly the same (within 1pt)
            if abs(prev.get("max_font", 0) - item.get("max_font", 0)) < 1.0:
                should_merge = True

        if prev["type"] == "reference" and item["type"] == "reference":
            should_merge = True
            
        if should_merge:
            if not prev["segments"][-1][0].endswith(" ") and not item["segments"][0][0].startswith(" "):
                prev["segments"][-1][0] += " "
                
            if prev["segments"][-1][1] == item["segments"][0][1]:
                prev["segments"][-1][0] += item["segments"][0][0]
                prev["segments"].extend(item["segments"][1:])
            else:
                prev["segments"].extend(item["segments"])
            
            prev["text"] = (prev["text"] + " " + item["text"]).strip()
            prev["lines"].extend(item["lines"])
            prev["bbox"] = [
                min(prev["bbox"][0], item["bbox"][0]),
                min(prev["bbox"][1], item["bbox"][1]),
                max(prev["bbox"][2], item["bbox"][2]),
                max(prev["bbox"][3], item["bbox"][3])
            ]
        else:
            merged_items.append(item)

    # Phase 3: Final formatting and visualization
    final_semantic_items = []
    for item in merged_items:
        if item["type"] == "reference":
            # Split merged references into individual ones
            current_ref_lines = []
            for line in item["lines"]:
                line_text = "".join([s["text"] for s in line["spans"]]).strip()
                # Detection pattern for new reference start or "References" title
                if re.match(r'^(?:\[\d+\]|\d+\.)', line_text) or line_text.lower() == "references":
                    if current_ref_lines:
                        # Create a sub-item for the previous reference
                        all_t = [t for l in current_ref_lines for t in l.get("spans", [])]
                        sub_bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                                    max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
                        
                        # Re-calculate segments for this sub-item
                        sub_segments = []
                        for l in current_ref_lines:
                            line_y = l["spans"][0]["origin"][1] if l["spans"] else 0
                            for span in l["spans"]:
                                style = get_span_style(span, median_size, line_y)
                                text = strip_non_standard_chars(span["text"])
                                if not text: continue
                                if not sub_segments: sub_segments.append([text, style])
                                else:
                                    if style == sub_segments[-1][1]: sub_segments[-1][0] += text
                                    else: sub_segments.append([text, style])
                        
                        final_semantic_items.append({
                            "type": "reference",
                            "bbox": sub_bbox,
                            "segments": sub_segments,
                            "text": "".join([s[0] for s in sub_segments]).strip(),
                            "lines": current_ref_lines
                        })
                    current_ref_lines = [line]
                else:
                    if not current_ref_lines: current_ref_lines = [line]
                    else: current_ref_lines.append(line)
            
            if current_ref_lines:
                # Last reference
                all_t = [t for l in current_ref_lines for t in l.get("spans", [])]
                sub_bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                            max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
                sub_segments = []
                for l in current_ref_lines:
                    line_y = l["spans"][0]["origin"][1] if l["spans"] else 0
                    for span in l["spans"]:
                        style = get_span_style(span, median_size, line_y)
                        text = strip_non_standard_chars(span["text"])
                        if not text: continue
                        if not sub_segments: sub_segments.append([text, style])
                        else:
                            if style == sub_segments[-1][1]: sub_segments[-1][0] += text
                            else: sub_segments.append([text, style])
                
                final_semantic_items.append({
                    "type": "reference",
                    "bbox": sub_bbox,
                    "segments": sub_segments,
                    "text": "".join([s[0] for s in sub_segments]).strip(),
                    "lines": current_ref_lines
                })
        else:
            final_semantic_items.append(item)

    # Process final items for output and visualization
    last_type = None
    type_consecutive_count = 0
    for item in final_semantic_items:
        block_type = item["type"]
        bbox = item["bbox"]
        segments = item["segments"]
        block_text_raw = item["text"]
        
        # Track consecutive blocks of the same type for alpha alternation
        if block_type == last_type:
            type_consecutive_count += 1
        else:
            type_consecutive_count = 0
            last_type = block_type

        color = semantic_color_map.get(block_type, [0, 255, 0, 60])
        
        # Alpha alternation for consecutive blocks of same type
        current_alpha = alpha_int
        if type_consecutive_count % 2 != 0:
            current_alpha = alpha_int // 2
        
        fill_color = tuple(list(color[:3]) + [current_alpha])
        
        # Precise visualization: draw per-span rectangles to highlight gaps
        for line in item["lines"]:
            for span in line["spans"]:
                s_bbox = span["bbox"]
                rects_to_draw.append({
                    "bbox": [s_bbox[0]*zoom, s_bbox[1]*zoom, s_bbox[2]*zoom, s_bbox[3]*zoom],
                    "fill": fill_color
                })
        
        type_label = block_type.capitalize()
        if type_label not in legend_items:
            legend_items[type_label] = tuple(list(color[:3]) + [255])
        
        block_id_num = extracted_block_counter
        block_id = f"b{block_id_num:03d}"
        extracted_block_counter += 1
        
        # Label position: logically first token (first span of first line)
        if item["lines"] and item["lines"][0]["spans"]:
            first_span = item["lines"][0]["spans"][0]
            label_pos = (first_span["bbox"][0]*zoom, first_span["bbox"][1]*zoom)
        else:
            label_pos = (bbox[0]*zoom, bbox[1]*zoom)
        
        labels_to_draw.append({
            "pos": label_pos,
            "text": str(block_id_num),
            "font": label_font,
            "bg_color": (255, 255, 255, 255),
            "border_color": (0, 0, 0, 255)
        })

        # Formatting Markdown text
        block_md = ""
        if block_type in ["paragraph", "heading"]:
            first_is_bold = segments[0][1]["bold"]
            if first_is_bold:
                bold_end_idx = -1
                for i in range(1, len(segments)):
                    if not segments[i][1]["bold"]:
                        bold_end_idx = i; break
                if bold_end_idx != -1:
                    bold_text = "".join([s[0] for s in segments[:bold_end_idx]]).strip()
                    # Forced line break for subheadings
                    if len(bold_text.split()) < 12 or re.match(r"^\d+(\.\d+)*\s", bold_text):
                        heading_md = format_segments_with_color_merging(segments[:bold_end_idx]).strip()
                        body_md = format_segments_with_color_merging(segments[bold_end_idx:]).lstrip()
                        block_md = heading_md + " \n\n " + body_md
                    else: block_md = format_segments_with_color_merging(segments)
                else:
                    if len(block_text_raw.split()) < 12 or re.match(r"^\d+(\.\d+)*\s", block_text_raw):
                         block_md = format_segments_with_color_merging(segments) + "\n\n"
                    else: block_md = format_segments_with_color_merging(segments)
            else: block_md = format_segments_with_color_merging(segments)
        elif block_type == "reference":
            raw_content = format_segments_with_color_merging(segments)
            # Bold "References" title if it exists
            raw_content = re.sub(r"(?i)(References)", r"**\1**", raw_content, count=1)
            # Forced line break after "References" title or individual entries
            block_md = raw_content.strip()
        else:
            block_md = format_segments_with_color_merging(segments)
            
        block_md = re.sub(r' +', ' ', block_md)
        full_block_md = f"<!-- block_id: {block_id} type: {block_type} -->\n{block_md}"
        
        if block_md.strip():
            page_content_parts.append(full_block_md.strip())
            
        # info.json now contains full Markdown text
        semantic_info.append({
            "id": block_id, "type": block_type, "bbox": bbox,
            "text": block_md
        })
                
    content = "\n\n".join(page_content_parts)
    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    # Use DRAW tool for final visualization
    if draw_iface:
        vis_img = draw_iface["draw_rects_with_alpha"](vis_img, rects_to_draw)
        vis_img = draw_iface["draw_labels"](vis_img, labels_to_draw)
        vis_img = draw_iface["append_legend"](vis_img, legend_items)
    else:
        # Basic fallback if DRAW tool is unavailable
        draw = ImageDraw.Draw(vis_img)
        for r in rects_to_draw: draw.rectangle(r["bbox"], fill=r["fill"])
        for l in labels_to_draw: draw.text(l["pos"], l["text"], fill=(0,0,0,255), font=l["font"])

    vis_img.save(page_dir / "extracted.png")
    return content, image_metadata, semantic_info

def extract_pdf_pages(pdf_path: Path, output_root: Path, page_spec: Optional[str] = None) -> List[Dict[str, Any]]:
    doc = fitz.open(str(pdf_path))
    extracted_pages = []
    pages = parse_page_spec(page_spec, doc.page_count)
    
    all_blocks = []
    for p_num in pages:
        all_blocks.extend(doc[p_num].get_text("dict")["blocks"])
    median_size = get_median_font_size(all_blocks)
    
    pages_dir = output_root / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    
    for page_num in pages:
        content, images, semantic = extract_single_pdf_page(doc, page_num, pages_dir, median_size, 51)
        extracted_pages.append({
            "page_num": page_num + 1, "content": content, "images": images, "semantic": semantic
        })
    doc.close()
    return extracted_pages
