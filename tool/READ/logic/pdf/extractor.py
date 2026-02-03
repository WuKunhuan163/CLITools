#!/usr/bin/env python3
import hashlib
import os
import re
import copy
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat
from logic.config import get_color
from .formatter import get_span_style, apply_style_to_text, format_segments_with_color_merging, strip_non_standard_chars
from .layout import parse_page_spec, get_median_font_size

def extract_single_pdf_page(doc: fitz.Document, page_num: int, output_pages_root: Path, median_size: float, alpha_int: int = 51, preference: str = "default") -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
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
    
    tags_dir = page_dir / "tags"
    tags_dir.mkdir(parents=True, exist_ok=True)
    
    # Path for the markdown file
    md_file_path = page_dir / "extracted.md"
    
    # 1. Save source images and PDF
    source_pdf_path = page_dir / "source.pdf"
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    new_doc.save(str(source_pdf_path))
    new_doc.close()
    
    source_png_path = page_dir / "source.png"
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(source_png_path))
    
    vis_img = Image.open(source_png_path).convert("RGBA")
    
    try:
        label_font = ImageFont.truetype("Arial.ttf", int(10 * zoom))
    except:
        label_font = ImageFont.load_default()

    # Get DRAW tool interface
    try:
        from tool.DRAW.logic.interface.main import get_interface as get_draw_interface
        draw_iface = get_draw_interface()
    except ImportError:
        draw_iface = None

    # 3. Images folder structure
    page_images_root = page_dir / "images"
    preprocessed_dir = page_images_root / "1_preprocessed"
    tokenized_dir = page_images_root / "2_tokenized"
    processed_dir = page_images_root / "3_processed"
    
    # Sub-folders for individual artifacts
    tk_items_dir = tokenized_dir / "items"
    pr_items_dir = processed_dir / "items"
    
    for d in [preprocessed_dir, tokenized_dir, processed_dir, tk_items_dir, pr_items_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Define semantic mapping to colors
    semantic_color_map = {
        "title": get_color("RGBA_RED", [255, 0, 0, 100]),
        "header": get_color("RGBA_PURPLE", [128, 0, 128, 100]),
        "footer": get_color("RGBA_MAGENTA", [255, 0, 255, 100]),
        "separator": get_color("RGBA_BLUE", [0, 0, 255, 100]),
        "unprocessed_text": get_color("RGBA_GRAY", [180, 180, 180, 100]),
        "unprocessed_image": get_color("RGBA_LIGHTBROWN", [160, 120, 90, 120]),
    }

    # Data for DRAW tool
    rects_to_draw = []
    labels_to_draw = []
    legend_items = {}

    # New Visualization Data for Images
    tokenized_vis_data = {"rects": [], "labels": []}
    processed_vis_data = {"rects": [], "labels": []}

    def add_image_label(labels_list, bbox, id_text, font, zoom_val):
        """Helper to position label such that its top-right is at item's top-left."""
        x, y = bbox[0] * zoom_val, bbox[1] * zoom_val
        # Temporary draw to calculate text width
        tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        t_bbox = tmp_draw.textbbox((0, 0), str(id_text), font=font)
        w = t_bbox[2] - t_bbox[0]
        # Top-right of background box (pos_x + w + 2, pos_y - 2) = (x, y)
        # So pos_x = x - w - 2, pos_y = y + 2
        labels_list.append({
            "pos": (x - w - 4, y + 2), # Extra 2px for safety
            "text": id_text,
            "font": font,
            "bg_color": (255, 255, 255, 255),
            "border_color": (0, 0, 0, 255)
        })

    # 4. Text Extraction (Initial tokens - now at word level)
    page_raw = page.get_text("rawdict")
    all_spans = []
    seen_tokens = set()
    
    for b in page_raw["blocks"]:
        if b.get("type") != 0: continue
        for line in b["lines"]:
            for span in line["spans"]:
                # Group characters into words based on spaces
                current_word_chars = []
                
                def flush_word(chars):
                    if not chars: return
                    text = "".join([c["c"] for c in chars])
                    if not text.strip(): return
                    
                    bbox = [
                        min(c["bbox"][0] for c in chars),
                        min(c["bbox"][1] for c in chars),
                        max(c["bbox"][2] for c in chars),
                        max(c["bbox"][3] for c in chars)
                    ]
                    origin = [chars[0]["origin"][0], chars[0]["origin"][1]]
                    
                    token_key = (text, tuple(map(lambda x: round(x, 1), bbox)))
                    if token_key in seen_tokens: return
                    seen_tokens.add(token_key)
                    
                    all_spans.append({
                        "text": text, "bbox": bbox,
                        "font": span["font"], "size": span["size"],
                        "color": span["color"], "flags": span["flags"],
                        "origin": origin
                    })

                for char in span["chars"]:
                    if char["c"] == " ":
                        flush_word(current_word_chars)
                        current_word_chars = []
                    else:
                        current_word_chars.append(char)
                flush_word(current_word_chars)

    # Assign original IDs to text tokens
    for i, span in enumerate(all_spans):
        span["original_id"] = f"text_{i+1:04d}"

    # 5. Salient Region Detection & Filtering
    img_for_detection = vis_img.copy().convert("RGB")
    img_data = np.array(img_for_detection)
    h, w, _ = img_data.shape
    
    # A. Detect Dominant Background Color (Sample corners)
    corners = [img_data[0,0], img_data[0,-1], img_data[-1,0], img_data[-1,-1]]
    bg_color = np.median(corners, axis=0).astype(np.uint8)
    
    # B. Generate Mask & Wipe Source
    # mask_overlay will highlight wiped pixels in Red
    mask = np.zeros((h, w), dtype=bool)
    
    def get_content_mask(region, color_hint=None):
        """Find pixels in region that differ from bg_color."""
        diff = np.abs(region.astype(float) - bg_color.astype(float))
        return np.mean(diff, axis=2) > 15 # Threshold for content
    
    # Wipe Text Spans
    for span in all_spans:
        bbox = span["bbox"]
        x0, y0, x1, y1 = [int(c * zoom) for c in bbox]
        x0, y0, x1, y1 = max(0, x0-1), max(0, y0-1), min(w, x1+1), min(h, y1+1)
        if x1 > x0 and y1 > y0:
            region = img_data[y0:y1, x0:x1]
            m = get_content_mask(region)
            mask[y0:y1, x0:x1] |= m
            
    # Wipe Image Objects
    img_infos = page.get_image_info(xrefs=True)
    for info in img_infos:
        i_bbox = info["bbox"]
        x0, y0, x1, y1 = [int(c * zoom) for c in i_bbox]
        x0, y0, x1, y1 = max(0, x0-1), max(0, y0-1), min(w, x1+1), min(h, y1+1)
        if x1 > x0 and y1 > y0:
            region = img_data[y0:y1, x0:x1]
            m = get_content_mask(region)
            mask[y0:y1, x0:x1] |= m

    # Save Preprocessing Visualizations
    overlay_img = img_for_detection.copy()
    overlay_data = np.array(overlay_img)
    overlay_data[mask] = [255, 0, 0] # Red
    # Blend 50%
    vis_overlay = Image.blend(img_for_detection, Image.fromarray(overlay_data), alpha=0.5)
    vis_overlay.save(preprocessed_dir / "1_mask_overlay.png")
    
    wiped_data = img_data.copy()
    wiped_data[mask] = bg_color
    wiped_img = Image.fromarray(wiped_data)
    wiped_img.save(preprocessed_dir / "2_wiped_source.png")

    # C. Extract Artifacts from Wiped Source
    img_gray = wiped_img.convert("L")
    bg_gray = int(np.mean(bg_color))
    # Artifacts are pixels that differ significantly from background gray
    bw = img_gray.point(lambda x: 255 if abs(x - bg_gray) > 20 else 0, '1')
    bw_dilated = bw.filter(ImageFilter.MaxFilter(size=5))
    
    artifact_bboxes = []
    downscale = 2
    small_bw = bw_dilated.resize((bw_dilated.width // downscale, bw_dilated.height // downscale), resample=Image.NEAREST)
    sw, sh = small_bw.size
    pixels = small_bw.load()
    visited = set()
    
    for y in range(sh):
        for x in range(sw):
            if pixels[x, y] == 255 and (x, y) not in visited:
                stack = [(x, y)]
                visited.add((x, y))
                min_x, min_y, max_x, max_y = x, y, x, y
                while stack:
                    cx, cy = stack.pop()
                    min_x, min_y = min(min_x, cx), min(min_y, cy)
                    max_x, max_y = max(max_x, cx), max(max_y, cy)
                    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < sw and 0 <= ny < sh and pixels[nx, ny] == 255 and (nx, ny) not in visited:
                            visited.add((nx, ny)); stack.append((nx, ny))
                
                art_bbox = [(min_x * downscale) / zoom, (min_y * downscale) / zoom,
                            ((max_x + 1) * downscale) / zoom, ((max_y + 1) * downscale) / zoom]
                
                if (art_bbox[2] - art_bbox[0]) > 2 and (art_bbox[3] - art_bbox[1]) > 2:
                    crop_bbox = [art_bbox[0]*zoom, art_bbox[1]*zoom, art_bbox[2]*zoom, art_bbox[3]*zoom]
                    region_img = img_for_detection.crop(crop_bbox).convert("RGB")
                    stat = ImageStat.Stat(region_img)
                    # Use difference from bg_color instead of just absolute variance
                    mean_diff = np.mean(np.abs(np.array(region_img).astype(float) - bg_color.astype(float)))
                    if mean_diff > 10: # Significant difference from background
                        artifact_bboxes.append({"bbox": art_bbox, "rationale": f"mean_diff={mean_diff:.2f}, stat={stat.stddev}"})

    # Generate 3_wiped_result.png
    if draw_iface and artifact_bboxes:
        items_for_draw = []
        for i, art in enumerate(artifact_bboxes):
            items_for_draw.append({"bbox": [c * zoom for c in art["bbox"]], "id": str(i + 1)})
        w_res = draw_iface["draw_result_with_legend"](
            vis_img, items_for_draw, "Wiped Artifacts", tuple(list(semantic_color_map["unprocessed_image"][:3]) + [255])
        )
        w_res.save(preprocessed_dir / "3_wiped_result.png")

    image_semantic_items = []
    raw_img_id_counter = 1
    for info in img_infos:
        i_bbox = list(info["bbox"])
        crop_bbox = [i_bbox[0]*zoom, i_bbox[1]*zoom, i_bbox[2]*zoom, i_bbox[3]*zoom]
        try:
            region_img = vis_img.crop(crop_bbox).convert("RGB")
            stat = ImageStat.Stat(region_img)
            # Stricter background filter
            is_background = (i_bbox[2]-i_bbox[0]) > page_rect.width * 0.8 and (i_bbox[3]-i_bbox[1]) > page_rect.height * 0.8
            
            if not is_background and any(s > 8.0 for s in stat.stddev) and any(m < 250 for m in stat.mean):
                orig_id = f"img_{raw_img_id_counter:04d}"
                raw_img_id_counter += 1
                img_item = {"bbox": i_bbox, "text": "[Image Object]", "type": "unprocessed_image", "original_id": orig_id, "rationale": f"stddev={stat.stddev}, mean={stat.mean}"}
                image_semantic_items.append(img_item)
                
                # Save to tokenized sub-folder
                region_img.save(tk_items_dir / f"{orig_id}.png")
        except: pass

    for art in artifact_bboxes:
        orig_id = f"art_{raw_img_id_counter:04d}"
        raw_img_id_counter += 1
        art_item = {"bbox": art["bbox"], "text": "[Detected Salient Region]", "type": "unprocessed_image", "original_id": orig_id, "rationale": art["rationale"]}
        image_semantic_items.append(art_item)
        
        # Save to tokenized sub-folder
        try:
            crop_bbox = [art["bbox"][0]*zoom, art["bbox"][1]*zoom, art["bbox"][2]*zoom, art["bbox"][3]*zoom]
            vis_img.crop(crop_bbox).convert("RGB").save(tk_items_dir / f"{orig_id}.png")
        except: pass

    # Populate tokenized_vis_data
    for item in image_semantic_items:
        bbox = item["bbox"]
        orig_id = item.get("original_id", "")
        id_num = "".join(filter(str.isdigit, orig_id))
        color = semantic_color_map["unprocessed_image"]
        tokenized_vis_data["rects"].append({
            "bbox": [bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom],
            "fill": tuple(list(color[:3]) + [150])
        })
        if draw_iface:
            add_image_label(tokenized_vis_data["labels"], bbox, id_num, label_font, zoom)

    # 6. Layout Engine Processing (ABC Pipeline)
    from .algorithm.settlement.academic_paper import LayoutEngine
    engine = LayoutEngine(page_rect.width, page_rect.height, median_size, preference)
    all_items = engine.segment_tokens(all_spans, images=image_semantic_items)
    
    all_items.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))

    page_content_parts = []
    semantic_info = []
    extracted_block_counter = 1

    # Tagging Visualization Data
    tags_found = set()
    tag_visuals = {} # tag_name -> List[rects]

    unprocessed_image_counter = 1
    for item in all_items:
        block_type = item["type"]
        bbox = item["bbox"]
        
        is_unprocessed = block_type.startswith("unprocessed_")
        
        # Save Unprocessed Image
        if block_type == "unprocessed_image":
            img_name = f"image_{unprocessed_image_counter:03d}.png"
            img_path = pr_items_dir / img_name
            unprocessed_image_counter += 1
            
            # Crop and save
            crop_bbox = [bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom]
            try:
                with Image.open(source_png_path) as source_img:
                    img_crop = source_img.crop(crop_bbox)
                    img_crop.save(img_path)
                item["image_path"] = f"images/3_processed/items/{img_name}"
                # Add to processed_vis_data
                processed_vis_data["rects"].append({
                    "bbox": [bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom],
                    "fill": tuple(list(semantic_color_map["unprocessed_image"][:3]) + [150])
                })
                if draw_iface:
                    add_image_label(processed_vis_data["labels"], bbox, str(unprocessed_image_counter - 1), label_font, zoom)
            except:
                pass

        # Collect tags from all sources
        tokens_to_check = []
        if "lines" in item:
            for line in item["lines"]:
                tokens_to_check.extend(line["spans"])
        if item.get("absorbed_tokens"):
            tokens_to_check.extend(item["absorbed_tokens"])
            
        for span in tokens_to_check:
            if "tags" in span:
                for t_name, t_val in span["tags"].items():
                    tags_found.add(t_name)
                    if t_name not in tag_visuals: tag_visuals[t_name] = []
                    s_bbox = span["bbox"]
                    tag_visuals[t_name].append({
                        "bbox": [s_bbox[0]*zoom, s_bbox[1]*zoom, s_bbox[2]*zoom, s_bbox[3]*zoom], 
                        "fill": (255, 255, 0, 150)
                    })

        # Regular Visualization
        color = semantic_color_map.get(block_type, [128, 128, 128])
        alpha = alpha_int if block_type in ["title", "header", "footer", "separator", "author"] else (color[3] if len(color) > 3 else 60)
        fill_color = tuple(list(color[:3]) + [alpha])
        
        if "lines" in item and item["lines"]:
            for line in item["lines"]:
                if block_type not in ["unprocessed_text"]:
                    # For settled text blocks, render the whole line (includes spaces)
                    l_bbox = line["bbox"]
                    rects_to_draw.append({"bbox": [l_bbox[0]*zoom, l_bbox[1]*zoom, l_bbox[2]*zoom, l_bbox[3]*zoom], "fill": fill_color})
                else:
                    # For unprocessed text, render individual words (no spaces)
                    for span in line["spans"]:
                        s_bbox = span["bbox"]
                        rects_to_draw.append({"bbox": [s_bbox[0]*zoom, s_bbox[1]*zoom, s_bbox[2]*zoom, s_bbox[3]*zoom], "fill": fill_color})
        else:
            rects_to_draw.append({"bbox": [bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom], "fill": fill_color})
        
        type_label = block_type.replace("unprocessed_", "Unprocessed ").capitalize()
        if "Unprocessed Text" in type_label: type_label = "Unprocessed Text"
        elif "Unprocessed Image" in type_label: type_label = "Unprocessed Image"
        if type_label not in legend_items: legend_items[type_label] = tuple(list(color[:3]) + [255])
        
        is_unprocessed = block_type.startswith("unprocessed_")
        # Separators should be settled but NOT numbered and NOT in MD
        is_numbered = not is_unprocessed and block_type != "separator"
        block_id = None
        
        if is_numbered:
            block_id_num = extracted_block_counter
            block_id = f"b{block_id_num:03d}"
            extracted_block_counter += 1
            
            label_pos = (bbox[0]*zoom, bbox[1]*zoom)
            labels_to_draw.append({"pos": label_pos, "text": str(block_id_num), "font": label_font, "bg_color": (255, 255, 255, 255), "border_color": (0, 0, 0, 255)})

        # Markdown
        block_md = ""
        if block_type == "title":
            block_md = f"# {format_segments_with_color_merging(item['segments']).strip()}"
        elif block_type in ["header", "footer"]:
            block_md = format_segments_with_color_merging(item["segments"]).strip()
            block_md = f"**{block_md}**" if item.get("subtype") == "DOI" else f"*{block_md}*"
        elif block_type == "author": block_md = item["text"]
            
        # Only add to markdown if it has valid text and is not a separator or unprocessed
        if block_md.strip() and not is_unprocessed and block_type != "separator":
            page_content_parts.append(f"<!-- block_id: {block_id} type: {block_type} -->\n{block_md}")
            
        info_entry = {"type": block_type, "bbox": bbox, "text": block_md if block_md else item.get("text", "")}
        if block_id: info_entry["id"] = block_id
        if "lines" in item: 
            info_entry["lines"] = item["lines"]
            # Propagate tags from spans to block level if block level tags are missing
            if "tags" not in item:
                block_tags = {}
                for line in item["lines"]:
                    for span in line["spans"]:
                        if "tags" in span:
                            for t_name, t_val in span["tags"].items():
                                if t_name not in block_tags:
                                    block_tags[t_name] = copy.deepcopy(t_val)
                                else:
                                    # Merge rationales if possible
                                    old_rat = block_tags[t_name].get("rationale", "")
                                    new_rat = t_val.get("rationale", "")
                                    if new_rat and new_rat not in old_rat:
                                        block_tags[t_name]["rationale"] = f"{old_rat}; {new_rat}"
                if block_tags: info_entry["tags"] = block_tags

        for field in ["subtype", "merged_texts", "rationale", "rationales", "tags", "image_path", "original_id", "merged_ids"]:
            if field == "tags" and "tags" in info_entry: continue # Already handled propagation
            if item.get(field): info_entry[field] = item[field]
        
        # If merged_ids exist, also add absorbed_ids
        if item.get("absorbed_tokens"):
            info_entry["absorbed_ids"] = [t["original_id"] for t in item["absorbed_tokens"]]
            
        semantic_info.append(info_entry)
                
    content = "\n\n".join(page_content_parts)
    with open(md_file_path, "w", encoding="utf-8") as f: f.write(content)
    with open(page_dir / "info.json", "w", encoding="utf-8") as f: json.dump({"page": actual_page_num, "semantic_blocks": semantic_info}, f, indent=2, ensure_ascii=False)
        
    if draw_iface:
        vis_img = draw_iface["draw_rects_with_alpha"](vis_img, rects_to_draw)
        vis_img = draw_iface["draw_labels"](vis_img, labels_to_draw)
        vis_img = draw_iface["append_legend"](vis_img, legend_items)
        vis_img.save(page_dir / "extracted.png")
        
        # Generate Tagging Images
        for t_name in tags_found:
            t_img = Image.open(source_png_path).convert("RGBA")
            t_img = draw_iface["draw_rects_with_alpha"](t_img, tag_visuals[t_name])
            t_img = draw_iface["append_legend"](t_img, {f"Tag: {t_name}": (255, 255, 0, 255)})
            t_img.save(tags_dir / f"{t_name}.png")
        
        # Generate tokenized.png and processed.png
        if tokenized_vis_data["rects"]:
            tk_img = Image.open(source_png_path).convert("RGBA")
            tk_img = draw_iface["draw_rects_with_alpha"](tk_img, tokenized_vis_data["rects"])
            tk_img = draw_iface["draw_labels"](tk_img, tokenized_vis_data["labels"])
            tk_img = draw_iface["append_legend"](tk_img, {"Tokenized Images": tuple(list(semantic_color_map["unprocessed_image"][:3]) + [255])})
            tk_img.save(tokenized_dir / "result.png")
            
        if processed_vis_data["rects"]:
            pr_img = Image.open(source_png_path).convert("RGBA")
            pr_img = draw_iface["draw_rects_with_alpha"](pr_img, processed_vis_data["rects"])
            pr_img = draw_iface["draw_labels"](pr_img, processed_vis_data["labels"])
            pr_img = draw_iface["append_legend"](pr_img, {"Processed Images": tuple(list(semantic_color_map["unprocessed_image"][:3]) + [255])})
            pr_img.save(processed_dir / "result.png")
    else:
        vis_img.save(page_dir / "extracted.png")

    return content, [], semantic_info

def extract_pdf_pages(pdf_path: Path, output_root: Path, page_spec: Optional[str] = None) -> List[Dict[str, Any]]:
    doc = fitz.open(str(pdf_path))
    pages = parse_page_spec(page_spec, doc.page_count)
    all_blocks = []
    for p_num in pages: all_blocks.extend(doc[p_num].get_text("dict")["blocks"])
    median_size = get_median_font_size(all_blocks)
    pages_dir = output_root / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    extracted_pages = []
    for page_num in pages:
        content, _, semantic = extract_single_pdf_page(doc, page_num, pages_dir, median_size, 51)
        extracted_pages.append({"page_num": page_num + 1, "content": content, "images": [], "semantic": semantic})
    doc.close()
    return extracted_pages
