#!/usr/bin/env python3
import hashlib
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import numpy as np
from logic.config import get_color
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
    
    # Subdirectories for organized steps
    raw_images_dir = page_images_dir / "0_raw_images"
    step1_dir = page_images_dir / "1_preprocessed"
    step2_dir = page_images_dir / "2_tokenized"
    step3_dir = page_images_dir / "3_processed"
    for d in [raw_images_dir, step1_dir, step2_dir, step3_dir]: d.mkdir(parents=True, exist_ok=True)
    
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
                img_path = raw_images_dir / img_filename
                
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

    from PIL import ImageFont
    try:
        label_font = ImageFont.truetype("Arial.ttf", int(10 * zoom))
    except:
        label_font = ImageFont.load_default()

    # 5. Text Extraction using Pipeline
    page_dict = page.get_text("rawdict")
    all_spans = []
    for b in page_dict["blocks"]:
        if b.get("type") != 0: continue
        for line in b["lines"]:
            for span in line["spans"]:
                all_spans.append({
                    "text": "".join([c["c"] for c in span.get("chars", [])]),
                    "bbox": list(span["bbox"]),
                    "font": span["font"],
                    "size": span["size"],
                    "color": span["color"],
                    "flags": span["flags"],
                    "origin": list(span["origin"]),
                    "chars": span.get("chars", [])
                })

    from .algorithm.pipeline.step1_tokenization.process import Preprocessor
    from .algorithm.pipeline.step2_tagging.process import Tagger
    from .algorithm.pipeline.step3_settlement.process import Settlement
    
    preprocessor = Preprocessor("/Applications/AITerminalTools")
    bg_color = preprocessor.get_background_color(vis_img)
    
    # --- Step 1: Preprocessing ---
    # 1.1 Calculate BBoxes
    glyph_boxes, actual_boxes = preprocessor.get_token_bboxes(np.array(vis_img), all_spans, zoom)
    
    if draw_iface:
        draw_iface["draw_rects_with_alpha"](vis_img, [{"bbox": b, "fill": (255, 0, 0, 128)} for b in glyph_boxes]).save(step1_dir / "1_glyph_bbox_overlay.png")
        
        # 1.3 Generate 2_actual_bbox_overlay.png (Original + grey glyph boxes + green actual boxes)
        actual_viz = draw_iface["draw_rects_with_alpha"](vis_img, [
            {"bbox": b, "fill": (200, 200, 200, 80)} for b in glyph_boxes
        ])
        actual_viz = draw_iface["draw_rects_with_alpha"](actual_viz, [
            {"bbox": b, "fill": (0, 255, 0, 128)} for b in actual_boxes
        ])
        actual_viz.save(step1_dir / "2_actual_bbox_overlay.png")
    
    # 1.2 Wiping
    wiped_img, text_mask = preprocessor.wipe_spans(vis_img, all_spans, zoom, bg_color=bg_color)
    wiped_img.save(step1_dir / "3_background_remaining.png")
    
    # 1.3 Artifacts
    artifact_bboxes = preprocessor.detect_artifacts(vis_img, wiped_img, bg_color)
    if draw_iface:
        a_img = wiped_img.convert("RGBA")
        a_rects = [{"bbox": b, "fill": (255, 255, 0, 100)} for b in artifact_bboxes]
        a_labels = [{"pos": (b[0], b[1]), "text": f"A{i+1}", "font": label_font} for i, b in enumerate(artifact_bboxes)]
        a_img = draw_iface["draw_rects_with_alpha"](a_img, a_rects)
        a_img = draw_iface["draw_labels"](a_img, a_labels)
        a_img.save(step1_dir / "4_wiped_result.png")

    # --- Step 2: Tokenization & Tagging ---
    from .algorithm.layout_engine import LayoutEngine
    engine = LayoutEngine(page_rect.width, page_rect.height)
    grouped_blocks = engine.segment_tokens(all_spans)
    
    tagger = Tagger(page_rect, median_size)
    tagged_items = tagger.tag_and_merge(grouped_blocks)
    
    # Visualize tokenization
    if draw_iface:
        t_img = vis_img.convert("RGBA")
        t_rects = []
        for item in tagged_items:
            color = semantic_color_map.get(item["type"], [0, 255, 0, 60])
            t_rects.append({"bbox": [c*zoom for c in item["bbox"]], "fill": tuple(list(color[:3]) + [alpha_int])})
        t_img = draw_iface["draw_rects_with_alpha"](t_img, t_rects)
        t_img.save(step2_dir / "result.png")

    # --- Step 3: Settlement ---
    settlement = Settlement(median_size)
    final_items = settlement.settle(tagged_items)
    
    # Final visualization
    if draw_iface:
        res_img = vis_img.convert("RGBA")
        res_rects = []
        res_labels = []
        for idx, item in enumerate(final_items):
            color = semantic_color_map.get(item["type"], [0, 255, 0, 60])
            res_rects.append({"bbox": [c*zoom for c in item["bbox"]], "fill": tuple(list(color[:3]) + [alpha_int])})
            res_labels.append({"pos": (item["bbox"][0]*zoom, item["bbox"][1]*zoom), "text": str(idx+1), "font": label_font})
        res_img = draw_iface["draw_rects_with_alpha"](res_img, res_rects)
        res_img = draw_iface["draw_labels"](res_img, res_labels)
        res_img = draw_iface["append_legend"](res_img, legend_items)
        res_img.save(step3_dir / "result.png")
        res_img.save(page_dir / "extracted.png")

    # Generate Markdown
    page_content_parts = []
    if page_images_content: page_content_parts.extend(page_images_content)
    
    semantic_info = []
    for idx, item in enumerate(final_items):
        md_text = item.get("md_text", item["text"])
        page_content_parts.append(f"<!-- block_id: b{idx+1:03d} type: {item['type']} -->\n{md_text}")
        semantic_info.append({
            "id": f"b{idx+1:03d}", 
            "type": item["type"], 
            "bbox": item["bbox"], 
            "text": md_text,
            "segments": item.get("segments", [])
        })
        
    # Save semantic.json
    import json
    with open(page_dir / "semantic.json", "w", encoding="utf-8") as f:
        json.dump(semantic_info, f, indent=2, ensure_ascii=False)
        
    content = "\n\n".join(page_content_parts)
    with open(md_file_path, "w", encoding="utf-8") as f: f.write(content)
    
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
