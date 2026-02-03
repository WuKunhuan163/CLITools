import sys
from PIL import Image, ImageDraw, ImageStat
import numpy as np
from pathlib import Path
import fitz

import io
def debug_wiping(pdf_path, page_num, output_path):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes())).convert("RGB")
    
    img_data = np.array(img)
    page_raw = page.get_text("rawdict")
    all_spans = []
    for b in page_raw["blocks"]:
        if b.get("type") != 0: continue
        for line in b["lines"]:
            for span in line["spans"]:
                all_spans.append(span)

    # Threshold-based wiping (replicating logic in extractor.py)
    for span in all_spans:
        bbox = span["bbox"]
        x0, y0, x1, y1 = [int(c * zoom) for c in bbox]
        pad = 1
        x0, y0, x1, y1 = x0-pad, y0-pad, x1+pad, y1+pad
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(img_data.shape[1], x1), min(img_data.shape[0], y1)
        if x1 > x0 and y1 > y0:
            region = img_data[y0:y1, x0:x1]
            mask = np.mean(region, axis=2) < 120
            region[mask] = [255, 255, 255]
            img_data[y0:y1, x0:x1] = region
            
    # Wipe image objects
    img_infos = page.get_image_info(xrefs=True)
    img_after_text_wipe = Image.fromarray(img_data)
    draw = ImageDraw.Draw(img_after_text_wipe)
    for info in img_infos:
        i_bbox = [info["bbox"][0]*zoom, info["bbox"][1]*zoom, info["bbox"][2]*zoom, info["bbox"][3]*zoom]
        draw.rectangle(i_bbox, fill=(255, 255, 255))
        
    img_after_text_wipe.save(output_path)
    print(f"Debug wiped image saved to: {output_path}")
    doc.close()

if __name__ == "__main__":
    pdf_path = "/Applications/AITerminalTools/tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    debug_wiping(pdf_path, 0, "debug_wiped.png")

