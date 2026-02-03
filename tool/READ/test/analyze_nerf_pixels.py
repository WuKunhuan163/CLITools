import fitz
import os
import sys
from PIL import Image, ImageDraw
import numpy as np

def analyze_token_pixels(pdf_path, page_num, target_text):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    zoom = 2
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img_data = np.array(img)

    # Get text dict
    blocks = page.get_text("rawdict")["blocks"]
    
    found_tokens = []
    for b in blocks:
        if b["type"] != 0: continue
        for line in b["lines"]:
            for span in line["spans"]:
                span_text = "".join([c["c"] for c in span["chars"]])
                if target_text in span_text:
                    found_tokens.append({
                        "span_text": span_text,
                        "bbox": span["bbox"],
                        "font": span["font"],
                        "size": span["size"],
                        "ascender": span["ascender"],
                        "descender": span["descender"],
                        "origin": span["origin"],
                        "chars": span["chars"]
                    })

    if not found_tokens:
        print(f"Token '{target_text}' not found on page {page_num+1}")
        return

    for i, token in enumerate(found_tokens):
        print(f"\n--- Analyzing Token {i+1}: '{token['span_text']}' ---")
        bbox = token["bbox"]
        print(f"BBox: {bbox}")
        print(f"Origin: {token['origin']}")
        print(f"Font: {token['font']}, Size: {token['size']}")
        print(f"Ascender: {token['ascender']}, Descender: {token['descender']}")
        
        # Calculate tighter height based on ascender/descender
        # span['ascender'] and span['descender'] are ratios relative to font size?
        # In fitz, span['origin'] is the baseline. 
        # The line height is roughly size * (ascender - descender).
        
        for char in token["chars"]:
            if char["c"] == target_text[0] or target_text in char["c"]:
                c_bbox = char["bbox"]
                print(f"  Char '{char['c']}' BBox: {c_bbox}")
                
                # Check pixels in this char bbox
                x0, y0, x1, y1 = [int(c * zoom) for c in c_bbox]
                region = img_data[y0:y1, x0:x1]
                
                # Find content pixels (not background)
                # Assuming background is white (255,255,255)
                # Use a threshold to find dark pixels
                gray_region = np.mean(region, axis=2)
                content_mask = gray_region < 200 # Content pixels are dark
                
                if np.any(content_mask):
                    rows = np.any(content_mask, axis=1)
                    cols = np.any(content_mask, axis=0)
                    rmin, rmax = np.where(rows)[0][[0, -1]]
                    cmin, cmax = np.where(cols)[0][[0, -1]]
                    
                    actual_y0 = y0 + rmin
                    actual_y1 = y0 + rmax
                    actual_x0 = x0 + cmin
                    actual_x1 = x0 + cmax
                    
                    print(f"  Actual Glyph BBox (pixels): ({actual_x0}, {actual_y0}, {actual_x1}, {actual_y1})")
                    print(f"  Actual Glyph BBox (PDF): ({actual_x0/zoom}, {actual_y0/zoom}, {actual_x1/zoom}, {actual_y1/zoom})")
                    print(f"  Vertical Buffer Top: {(actual_y0/zoom) - c_bbox[1]:.2f} pts")
                    print(f"  Vertical Buffer Bottom: {c_bbox[3] - (actual_y1/zoom):.2f} pts")
                    
                    # Visualize actual glyph
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([actual_x0, actual_y0, actual_x1, actual_y1], outline="blue", width=1)
                else:
                    print("  No content found in char bbox!")
    
    debug_path = "tool/READ/tmp/analyze_nerf_pixels.png"
    img.save(debug_path)
    print(f"\nDebug image saved to {debug_path}")

if __name__ == "__main__":
    pdf = "tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    analyze_token_pixels(pdf, 0, "NeRF")

