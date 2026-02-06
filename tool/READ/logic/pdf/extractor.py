import os
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Tuple
from logic.config import get_color
from .formatter import get_span_style, apply_style_to_text, process_text_linebreaks, format_segments_with_color_merging, strip_non_standard_chars, is_sentence_complete
from .layout import parse_page_spec, get_median_font_size

def extract_single_pdf_page(doc: Any, page_num: int, output_pages_root: Path, median_size: float, alpha_int: int = 51) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    from tool.FITZ.logic.pdf.wrapper import FitzWrapper
    import fitz
    page = doc[page_num]
    page_rect = page.rect
    actual_page_num = page_num + 1
    page_dir = output_pages_root / f"page_{actual_page_num:03d}"
    page_dir.mkdir(parents=True, exist_ok=True)
    md_file_path = page_dir / "extracted.md"
    
    source_pdf_path = page_dir / "source.pdf"
    new_doc = FitzWrapper.open() # Create new empty doc
    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    FitzWrapper.save(new_doc, str(source_pdf_path))
    new_doc.close()
    
    source_png_path = page_dir / "source.png"
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = FitzWrapper.get_pixmap(page, matrix=mat)
    pix.save(str(source_png_path))
    
    vis_img = Image.open(source_png_path).convert("RGBA")
    
    # 1. Extract Spans First
    page_dict = page.get_text("rawdict")
    all_spans = []
    for b in page_dict["blocks"]:
        if b.get("type") != 0: continue
        for line in b["lines"]:
            for span in line["spans"]:
                all_spans.append({
                    "text": "".join([c["c"] for c in span.get("chars", [])]),
                    "bbox": list(span["bbox"]), "font": span["font"], "size": span["size"],
                    "color": span["color"], "flags": span["flags"], "origin": list(span["origin"]),
                    "chars": span.get("chars", [])
                })

    try:
        from tool.DRAW.logic.interface.main import get_interface as get_draw_interface
        draw_iface = get_draw_interface()
    except ImportError: draw_iface = None

    page_viz_dir = page_dir / "analysis_viz"
    page_viz_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Define Pipeline Step Names
    STEP1_NAME = "step1_tokenization"
    STEP2_NAME = "step2_semantics"
    
    step1_dir = page_viz_dir / STEP1_NAME
    step2_dir = page_viz_dir / STEP2_NAME
    for d in [step1_dir, step2_dir]: d.mkdir(parents=True, exist_ok=True)
    
    semantic_color_map = {
        "title": get_color("RGBA_RED", [255, 0, 0, 100]), "heading": get_color("RGBA_ORANGE", [255, 165, 0, 100]),
        "paragraph": get_color("RGBA_GREEN", [0, 255, 0, 60]), "reference": get_color("RGBA_MAGENTA", [255, 0, 255, 100]),
        "header": get_color("RGBA_BLUE", [0, 0, 255, 100]), "footer": get_color("RGBA_GRAY", [128, 128, 128, 100]),
        "image": get_color("RGBA_YELLOW", [255, 255, 0, 100]), "table": get_color("RGBA_CYAN", [0, 255, 255, 100]),
    }

    from .algorithm.pipeline.step1_tokenization.process import Preprocessor
    from .algorithm.pipeline.step2_semantics.process import SemanticsEngine
    
    preprocessor = Preprocessor("/Applications/AITerminalTools")
    bg_color = preprocessor.get_background_color(vis_img)

    # --- Step 1: Tokenization ---
    glyph_boxes, actual_boxes, offsets = preprocessor.get_token_bboxes(np.array(vis_img), all_spans, zoom)
    
    # 4. Extract Image Metadata and Pixel-Aware Masks
    # Use get_text("dict") to find and extract images (including inline ones)
    page_dict_for_imgs = page.get_text("dict")
    image_blocks = [b for b in page_dict_for_imgs["blocks"] if b["type"] == 1]
    
    image_bboxes = []
    image_masks = [] # List of (bbox, mask_array, id)
    
    raw_images_dir = step1_dir / "2.1_raw_images"
    raw_images_dir.mkdir(parents=True, exist_ok=True)
    
    import io
    for i, b in enumerate(image_blocks):
        bbox = b["bbox"]
        zoomed_bbox = [bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom]
        image_bboxes.append(zoomed_bbox)
        img_id = f"I{i+1}"
        
        try:
            img_bytes = b["image"]
            img = Image.open(io.BytesIO(img_bytes))
            img.save(raw_images_dir / f"{img_id}.png")
            
            # Create mask from non-white pixels
            mask_data = np.array(img.convert("RGB"))
            content_mask = np.any(np.abs(mask_data.astype(float) - 255) > 20, axis=2)
            image_masks.append({"bbox": zoomed_bbox, "mask": content_mask, "id": img_id})
        except: pass

    try:
        label_font = ImageFont.truetype("Arial.ttf", int(10 * zoom))
    except: label_font = ImageFont.load_default()

    # --- Step 1: Tokenization ---
    glyph_boxes, actual_boxes, offsets = preprocessor.get_token_bboxes(np.array(vis_img), all_spans, zoom)
    
    if draw_iface:
        draw_iface["draw_rects_with_alpha"](vis_img, [{"bbox": b, "fill": (255, 0, 0, 128)} for b in glyph_boxes]).save(step1_dir / "1.1_raw_text_glyph_bbox_overlay.png")
        actual_viz = draw_iface["draw_rects_with_alpha"](vis_img, [{"bbox": b, "fill": (200, 200, 200, 80)} for b in glyph_boxes])
        draw_iface["draw_rects_with_alpha"](actual_viz, [{"bbox": b, "fill": (0, 255, 0, 128)} for b in actual_boxes]).save(step1_dir / "1.2_raw_text_actual_bbox_overlay.png")
        
        # Pixel-Aware Image Overlay
        img_ov = vis_img.convert("RGBA")
        ov_data = np.array(img_ov)
        ov_labels = []
        for im_data in image_masks:
            ibox, imask, iid = im_data["bbox"], im_data["mask"], im_data["id"]
            ix0, iy0, ix1, iy1 = [int(round(c)) for c in ibox]
            # Resize mask to fit zoomed bbox
            mask_img = Image.fromarray(imask).resize((max(1, ix1-ix0), max(1, iy1-iy0)), Image.NEAREST)
            m_arr = np.array(mask_img)
            region = ov_data[iy0:iy1, ix0:ix1]
            if region.shape[:2] == m_arr.shape:
                region[m_arr] = [255, 255, 0, 128]
            ov_labels.append({"pos": (ix0, iy0), "text": iid, "font": label_font})
        
        ov_img = Image.fromarray(ov_data)
        if draw_iface:
            draw_iface["draw_labels"](ov_img, ov_labels).save(step1_dir / "2.2_raw_images_overlay.png")
        else:
            ov_img.save(step1_dir / "2.2_raw_images_overlay.png")
    
    wiped_img, text_mask, wipe_offsets = preprocessor.wipe_content(vis_img, all_spans, image_masks, zoom, bg_color=bg_color)
    wiped_img.save(step1_dir / "3_background_remaining.png")
    
    artifact_bboxes = preprocessor.detect_artifacts(vis_img, wiped_img, bg_color)
    if draw_iface:
        a_img = wiped_img.convert("RGBA")
        a_rects = [{"bbox": b, "fill": (255, 255, 0, 100)} for b in artifact_bboxes]
        a_labels = [{"pos": (b[0], b[1]), "text": f"A{i+1}", "font": label_font} for i, b in enumerate(artifact_bboxes)]
        a_img = draw_iface["draw_rects_with_alpha"](a_img, a_rects)
        draw_iface["draw_labels"](a_img, a_labels).save(step1_dir / "4_background_artifact.png")
        
        # Save individual artifacts to 4_background_artifacts/
        artifacts_dir = step1_dir / "4_background_artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        for i, b in enumerate(artifact_bboxes):
            try:
                ax0, ay0, ax1, ay1 = [int(round(c)) for c in b]
                if ax1 > ax0 and ay1 > ay0:
                    # Artifacts are by definition in the background, so use wiped_img
                    a_crop = wiped_img.crop((ax0, ay0, ax1, ay1))
                    a_crop.save(artifacts_dir / f"A{i+1}.png")
            except: pass

    if draw_iface:
        c_img = vis_img.convert("RGBA")
        c_rects, c_labels = [], []
        # Text (Use GLYPH bboxes for combined elements view)
        for b in glyph_boxes: c_rects.append({"bbox": b, "fill": (0, 255, 0, 80)})
        # Raw Images
        for i, b in enumerate(image_bboxes):
            c_rects.append({"bbox": b, "fill": (255, 255, 0, 80)})
            c_labels.append({"pos": (b[0], b[1]), "text": f"I{i+1}", "font": label_font})
        # Artifacts
        for i, b in enumerate(artifact_bboxes):
            c_rects.append({"bbox": b, "fill": (255, 0, 255, 80)})
            c_labels.append({"pos": (b[0], b[1]), "text": f"A{i+1}", "font": label_font})
            
        legend = {"Text (Glyph)": (0, 255, 0, 255), "Raw Image": (255, 255, 0, 255), "Artifact": (255, 0, 255, 255)}
        c_img = draw_iface["draw_rects_with_alpha"](c_img, c_rects)
        c_img = draw_iface["draw_labels"](c_img, c_labels)
        draw_iface["append_legend"](c_img, legend).save(step1_dir / "5_combined_elements.png")

    tokens = preprocessor.join_tokens(actual_boxes, glyph_boxes, image_bboxes, artifact_bboxes, all_spans, vis_img=vis_img)
    with open(step1_dir / "analysis.json", "w", encoding="utf-8") as f:
        json.dump({"offsets": offsets, "tokens": tokens}, f, indent=2)

    if draw_iface:
        # 6. Semantic Images Visualization
        # 50% bleached background
        bleached = vis_img.copy()
        bleached_data = np.array(bleached)
        bleached_data[..., 3] = (bleached_data[..., 3] * 0.5).astype(np.uint8)
        bleached = Image.fromarray(bleached_data)
        
        s_rects, s_labels = [], []
        for tk in tokens:
            if tk["type"] == "visual":
                if tk.get("subtype") == "line":
                    s_rects.append({"bbox": tk["bbox"], "fill": (255, 0, 255, 128)}) # Magenta for lines
                    s_labels.append({"pos": (tk["bbox"][0], tk["bbox"][1]), "text": tk["id"], "font": label_font})
                elif tk.get("subtype") == "box":
                    s_rects.append({"bbox": tk["bbox"], "fill": (0, 255, 255, 128)}) # Cyan for boxes
                    s_labels.append({"pos": (tk["bbox"][0], tk["bbox"][1]), "text": tk["id"], "font": label_font})
        
        s_img = draw_iface["draw_rects_with_alpha"](bleached, s_rects)
        s_img = draw_iface["draw_labels"](s_img, s_labels)
        legend_6 = {"Line": (255, 0, 255, 255), "Box": (0, 255, 255, 255)}
        draw_iface["append_legend"](s_img, legend_6).save(step1_dir / "6_semantic_images.png")

        # 7. Merged Image Tokens
        t_img = vis_img.convert("RGBA")
        t_rects, t_labels = [], []
        
        # Create directory for individual merged image tokens
        merged_tokens_dir = step1_dir / "7_merged_image_tokens"
        merged_tokens_dir.mkdir(parents=True, exist_ok=True)
        
        # Load component images for composition
        comp_images = {}
        for f in raw_images_dir.glob("*.png"):
            comp_images[f.stem] = Image.open(f).convert("RGBA")
        for f in artifacts_dir.glob("*.png"):
            comp_images[f.stem] = Image.open(f).convert("RGBA")

        # Map component IDs to their original bboxes for relative positioning
        comp_bboxes = {}
        for i, b in enumerate(image_bboxes): comp_bboxes[f"I{i+1}"] = b
        for i, b in enumerate(artifact_bboxes): comp_bboxes[f"A{i+1}"] = b

        # Map text IDs for absorption composition
        text_tokens_map = {tk["id"]: tk for tk in tokens if tk["type"] == "text"}

        for tk in tokens:
            if tk["type"] == "visual":
                if tk.get("subtype") == "line":
                    t_rects.append({"bbox": tk["bbox"], "fill": (255, 0, 255, 100)}) 
                elif tk.get("subtype") == "box":
                    t_rects.append({"bbox": tk["bbox"], "fill": (0, 255, 255, 100)})
                else:
                    t_rects.append({"bbox": tk["bbox"], "fill": (255, 255, 0, 100)}) # Yellow for blocks
                t_labels.append({"pos": (tk["bbox"][0], tk["bbox"][1]), "text": tk["id"], "font": label_font})
                
                # Compose merged token image from components
                try:
                    # Apply +1 padding to right and bottom boundaries to handle PIL's exclusive crop
                    tx0, ty0, tx1, ty1 = [int(round(c)) for c in tk["bbox"]]
                    tx1 += 1
                    ty1 += 1
                    
                    if tx1 > tx0 and ty1 > ty0:
                        # Create canvas with background color
                        canvas = Image.new("RGBA", (tx1 - tx0, ty1 - ty0), bg_color + (255,))
                        
                        # 1. Paste Image/Artifact Components
                        for cid in tk.get("comp_ids", []):
                            if cid in comp_images and cid in comp_bboxes:
                                cimg = comp_images[cid]
                                cbbox = comp_bboxes[cid]
                                
                                # Resize component image to match its zoomed bbox size
                                target_w = int(round(cbbox[2] - cbbox[0]))
                                target_h = int(round(cbbox[3] - cbbox[1]))
                                if target_w > 0 and target_h > 0:
                                    if cimg.size != (target_w, target_h):
                                        cimg = cimg.resize((target_w, target_h), Image.LANCZOS)
                                
                                # Relative position on canvas
                                rel_x = int(round(cbbox[0] - tx0))
                                rel_y = int(round(cbbox[1] - ty0))
                                canvas.paste(cimg, (rel_x, rel_y), cimg)
                        
                        # 2. Paste Absorbed Text Tokens (Clipped from original vis_img)
                        for tid in tk.get("absorbed_text_ids", []):
                            if tid in text_tokens_map:
                                ttk = text_tokens_map[tid]
                                wbox = ttk["bbox"]
                                # Also include +1 padding for absorbed text crops
                                wx0, wy0, wx1, wy1 = [int(round(c)) for c in wbox]
                                wx1 += 1
                                wy1 += 1
                                
                                if wx1 > wx0 and wy1 > wy0:
                                    # Crop from original vis_img (which contains the text)
                                    text_crop = vis_img.crop((wx0, wy0, wx1, wy1)).convert("RGBA")
                                    # Relative position on canvas
                                    rel_x = int(round(wbox[0] - tx0))
                                    rel_y = int(round(wbox[1] - ty0))
                                    canvas.paste(text_crop, (rel_x, rel_y), text_crop)

                        canvas.save(merged_tokens_dir / f"{tk['id']}.png")
                except Exception as e:
                    print(f"Warning: Failed to compose image token {tk['id']}: {e}")

            elif tk["type"] == "text":
                # Use GLYPH bbox for tokenization result visualization
                t_rects.append({"bbox": tk["glyph_bbox"], "fill": (0, 255, 0, 60)})
        t_img = draw_iface["draw_rects_with_alpha"](t_img, t_rects)
        t_img = draw_iface["draw_labels"](t_img, t_labels)
        
        legend_8 = {"Word (Glyph)": (0, 255, 0, 255), "Visual Block": (255, 255, 0, 255), "Line": (255, 0, 255, 255), "Box": (0, 255, 255, 255)}
        draw_iface["append_legend"](t_img, legend_8).save(step1_dir / "8_tokenization_result.png")

    # --- Step 2: Semantics ---
    semantics = SemanticsEngine(page_rect, median_size, "/Applications/AITerminalTools")
    final_items = semantics.process(tokens, step2_dir, zoom)

    page_content_parts, semantic_info = [], []
    for idx, item in enumerate(final_items):
        md_text = item.get("md_text", item["text"])
        page_content_parts.append(f"<!-- block_id: b{idx+1:03d} type: {item['type']} -->\n{md_text}")
        semantic_info.append({"id": f"b{idx+1:03d}", "type": item["type"], "bbox": item["bbox"], "text": md_text, "segments": item.get("segments", [])})
        
    with open(page_dir / "semantic.json", "w", encoding="utf-8") as f: json.dump(semantic_info, f, indent=2, ensure_ascii=False)
    content = "\n\n".join(page_content_parts)
    with open(md_file_path, "w", encoding="utf-8") as f: f.write(content)
    
    return content, [], semantic_info
