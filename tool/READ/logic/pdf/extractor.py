import fitz
import os
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Tuple
from logic.config import get_color
from .formatter import get_span_style, apply_style_to_text, process_text_linebreaks, format_segments_with_color_merging, strip_non_standard_chars, is_sentence_complete
from .layout import parse_page_spec, get_median_font_size

def extract_single_pdf_page(doc: fitz.Document, page_num: int, output_pages_root: Path, median_size: float, alpha_int: int = 51) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    page = doc[page_num]
    page_rect = page.rect
    actual_page_num = page_num + 1
    page_dir = output_pages_root / f"page_{actual_page_num:03d}"
    page_dir.mkdir(parents=True, exist_ok=True)
    md_file_path = page_dir / "extracted.md"
    
    source_pdf_path = page_dir / "source.pdf"
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    new_doc.save(str(source_pdf_path)); new_doc.close()
    
    source_png_path = page_dir / "source.png"
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat); pix.save(str(source_png_path))
    vis_img = Image.open(source_png_path).convert("RGBA")
    
    try:
        from tool.DRAW.logic.interface.main import get_interface as get_draw_interface
        draw_iface = get_draw_interface()
    except ImportError: draw_iface = None

    page_images_dir = page_dir / "images"
    page_images_dir.mkdir(parents=True, exist_ok=True)
    step1_dir = page_images_dir / "1_tokenized"
    step2_dir = page_images_dir / "2_semantic"
    step3_dir = page_images_dir / "3_processed"
    for d in [step1_dir, step2_dir, step3_dir]: d.mkdir(parents=True, exist_ok=True)
    
    semantic_color_map = {
        "title": get_color("RGBA_RED", [255, 0, 0, 100]), "heading": get_color("RGBA_ORANGE", [255, 165, 0, 100]),
        "paragraph": get_color("RGBA_GREEN", [0, 255, 0, 60]), "reference": get_color("RGBA_MAGENTA", [255, 0, 255, 100]),
        "header": get_color("RGBA_BLUE", [0, 0, 255, 100]), "footer": get_color("RGBA_GRAY", [128, 128, 128, 100]),
        "image": get_color("RGBA_YELLOW", [255, 255, 0, 100]), "table": get_color("RGBA_CYAN", [0, 255, 255, 100]),
    }

    rects_to_draw, labels_to_draw, legend_items = [], [], {}

    # 4. Extract Images and BBoxes
    image_info_list = page.get_image_info()
    image_bboxes = []
    page_images_content = []
    for info in image_info_list:
        bbox = info["bbox"]
        image_bboxes.append([bbox[0]*zoom, bbox[1]*zoom, bbox[2]*zoom, bbox[3]*zoom])
        
    image_metadata = []
    for idx, info in enumerate(image_info_list):
        image_metadata.append({"page": actual_page_num, "index": idx + 1, "bbox": info["bbox"], "type": "unknown"})

    try:
        label_font = ImageFont.truetype("Arial.ttf", int(10 * zoom))
    except: label_font = ImageFont.load_default()

    # 5. Text Extraction
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

    from .algorithm.pipeline.step1_tokenization.process import Preprocessor
    from .algorithm.pipeline.step2_tagging.process import Tagger
    from .algorithm.pipeline.step3_settlement.process import Settlement
    
    preprocessor = Preprocessor("/Applications/AITerminalTools")
    bg_color = preprocessor.get_background_color(vis_img)
    
    # --- Step 1: Tokenization ---
    glyph_boxes, actual_boxes, offsets = preprocessor.get_token_bboxes(np.array(vis_img), all_spans, zoom)
    with open(step1_dir / "analysis.json", "w", encoding="utf-8") as f:
        json.dump({"offsets": offsets, "glyph_boxes_count": len(glyph_boxes), "actual_boxes_count": len(actual_boxes), "image_boxes_count": len(image_bboxes)}, f, indent=2)
    
    if draw_iface:
        draw_iface["draw_rects_with_alpha"](vis_img, [{"bbox": b, "fill": (255, 0, 0, 128)} for b in glyph_boxes]).save(step1_dir / "1.1_raw_text_glyph_bbox_overlay.png")
        actual_viz = draw_iface["draw_rects_with_alpha"](vis_img, [{"bbox": b, "fill": (200, 200, 200, 80)} for b in glyph_boxes])
        draw_iface["draw_rects_with_alpha"](actual_viz, [{"bbox": b, "fill": (0, 255, 0, 128)} for b in actual_boxes]).save(step1_dir / "1.2_raw_text_actual_bbox_overlay.png")
        draw_iface["draw_rects_with_alpha"](vis_img, [{"bbox": b, "fill": (255, 255, 0, 128)} for b in image_bboxes]).save(step1_dir / "2_raw_images_overlay.png")
    
    wiped_img, text_mask, wipe_offsets = preprocessor.wipe_content(vis_img, all_spans, image_bboxes, zoom, bg_color=bg_color)
    wiped_img.save(step1_dir / "3_background_remaining.png")
    
    artifact_bboxes = preprocessor.detect_artifacts(vis_img, wiped_img, bg_color)
    if draw_iface:
        a_img = wiped_img.convert("RGBA")
        a_rects = [{"bbox": b, "fill": (255, 255, 0, 100)} for b in artifact_bboxes]
        a_labels = [{"pos": (b[0], b[1]), "text": f"A{i+1}", "font": label_font} for i, b in enumerate(artifact_bboxes)]
        a_img = draw_iface["draw_rects_with_alpha"](a_img, a_rects)
        draw_iface["draw_labels"](a_img, a_labels).save(step1_dir / "4_wiped_result.png")

    if draw_iface:
        c_img = vis_img.convert("RGBA")
        c_rects = [{"bbox": b, "fill": (0, 255, 0, 80)} for b in actual_boxes] + [{"bbox": b, "fill": (255, 255, 0, 80)} for b in image_bboxes] + [{"bbox": b, "fill": (255, 0, 255, 80)} for b in artifact_bboxes]
        legend = {"Text (Heuristic)": (0, 255, 0, 255), "Raw Image": (255, 255, 0, 255), "Artifact": (255, 0, 255, 255)}
        c_img = draw_iface["draw_rects_with_alpha"](c_img, c_rects)
        draw_iface["append_legend"](c_img, legend).save(step1_dir / "5_combined_elements.png")

    tokens = preprocessor.join_tokens(actual_boxes, image_bboxes, artifact_bboxes)
    if draw_iface:
        t_img = vis_img.convert("RGBA")
        t_rects = [{"bbox": t["bbox"], "fill": (0, 255, 0, 80) if t["type"] == "text" else (255, 255, 0, 80) if t["type"] == "image" else (255, 0, 255, 80)} for t in tokens]
        draw_iface["draw_rects_with_alpha"](t_img, t_rects).save(step1_dir / "6_tokenization_result.png")

    # --- Step 2: Semantic & Settlement ---
    from .algorithm.layout_engine import LayoutEngine
    engine = LayoutEngine(page_rect.width, page_rect.height)
    grouped_blocks = engine.segment_tokens(all_spans)
    tagger = Tagger(page_rect, median_size)
    tagged_items = tagger.tag_and_merge(grouped_blocks)
    
    settlement = Settlement(median_size)
    final_items = settlement.settle(tagged_items)
    
    if draw_iface:
        res_img = vis_img.convert("RGBA")
        res_rects, res_labels = [], []
        for idx, item in enumerate(final_items):
            color = semantic_color_map.get(item["type"], [0, 255, 0, 60])
            res_rects.append({"bbox": [c*zoom for c in item["bbox"]], "fill": tuple(list(color[:3]) + [alpha_int])})
            res_labels.append({"pos": (item["bbox"][0]*zoom, item["bbox"][1]*zoom), "text": str(idx+1), "font": label_font})
        res_img = draw_iface["draw_rects_with_alpha"](res_img, res_rects)
        res_img = draw_iface["draw_labels"](res_img, res_labels)
        draw_iface["append_legend"](res_img, legend_items).save(step3_dir / "result.png")
        res_img.save(page_dir / "extracted.png")

    page_content_parts, semantic_info = [], []
    for idx, item in enumerate(final_items):
        md_text = item.get("md_text", item["text"])
        page_content_parts.append(f"<!-- block_id: b{idx+1:03d} type: {item['type']} -->\n{md_text}")
        semantic_info.append({"id": f"b{idx+1:03d}", "type": item["type"], "bbox": item["bbox"], "text": md_text, "segments": item.get("segments", [])})
        
    with open(page_dir / "semantic.json", "w", encoding="utf-8") as f: json.dump(semantic_info, f, indent=2, ensure_ascii=False)
    content = "\n\n".join(page_content_parts)
    with open(md_file_path, "w", encoding="utf-8") as f: f.write(content)
    
    return content, image_metadata, semantic_info
