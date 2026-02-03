import fitz
from PIL import Image, ImageDraw, ImageStat
import numpy as np
import os

def test_glyph_wiping(pdf_path, page_num, output_prefix):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    zoom = 2
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img_data = np.array(img)
    h, w, _ = img_data.shape

    # Get all text spans
    blocks = page.get_text("rawdict")["blocks"]
    all_spans = []
    for b in blocks:
        if b["type"] != 0: continue
        for line in b["lines"]:
            all_spans.extend(line["spans"])

    # Method 1: BBox Wiping (What we had before)
    img_bbox_wiped = img_data.copy()
    for span in all_spans:
        x0, y0, x1, y1 = [int(c * zoom) for c in span["bbox"]]
        img_bbox_wiped[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] = [255, 255, 255]
    Image.fromarray(img_bbox_wiped).save(f"{output_prefix}_bbox_wiped.png")

    # Method 2: Glyph Wiping (New proposal)
    img_glyph_wiped = img_data.copy()
    for span in all_spans:
        # For each span, find actual dark pixels
        x0, y0, x1, y1 = [int(c * zoom) for c in span["bbox"]]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        
        if x1 <= x0 or y1 <= y0: continue
        
        region = img_data[y0:y1, x0:x1]
        gray = np.mean(region, axis=2)
        mask = gray < 200 # Content pixels
        
        if np.any(mask):
            # Find the tight glyph bbox within the span bbox
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            
            # Wipe ONLY the glyph area
            # We can add 1px padding
            p = 1
            gy0, gy1 = y0 + rmin - p, y0 + rmax + p
            gx0, gx1 = x0 + cmin - p, x0 + cmax + p
            img_glyph_wiped[max(0, gy0):min(h, gy1), max(0, gx0):min(w, gx1)] = [255, 255, 255]

    Image.fromarray(img_glyph_wiped).save(f"{output_prefix}_glyph_wiped.png")
    
    # Method 3: Pixel-wise Wiping (Even more precise)
    img_pixel_wiped = img_data.copy()
    for span in all_spans:
        x0, y0, x1, y1 = [int(c * zoom) for c in span["bbox"]]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 <= x0 or y1 <= y0: continue
        
        region = img_pixel_wiped[y0:y1, x0:x1]
        gray = np.mean(region, axis=2)
        mask = gray < 220 # Character pixels are usually quite dark
        # Only wipe pixels that are dark (part of a character)
        region[mask] = [255, 255, 255]
        img_pixel_wiped[y0:y1, x0:x1] = region
        
    Image.fromarray(img_pixel_wiped).save(f"{output_prefix}_pixel_wiped.png")

    print(f"Test complete. Results saved with prefix {output_prefix}")

if __name__ == "__main__":
    pdf = "tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    test_glyph_wiping(pdf, 0, "tool/READ/tmp/wiping_test")


