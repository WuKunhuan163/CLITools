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
    draw = ImageDraw.Draw(img)

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

    # Focus ONLY on the first token (Title)
    token = found_tokens[0]
    print(f"\n--- Analyzing Title Token: '{token['span_text'].strip()}' ---")
    bbox = token["bbox"]
    origin = token["origin"]
    print(f"BBox: {bbox}")
    print(f"Origin: {origin}")
    print(f"Font: {token['font']}, Size: {token['size']}")
    print(f"Ascender: {token['ascender']}, Descender: {token['descender']}")
    
    # Draw PDF BBox for Title Span
    tx0, ty0, tx1, ty1 = [int(c * zoom) for c in bbox]
    draw.rectangle([tx0, ty0, tx1, ty1], outline="red", width=2)
    
    # Analyze characters in 'NeRF'
    word_to_analyze = "NeRF"
    current_char_idx = 0
    
    word_glyph_bbox = [float('inf'), float('inf'), float('-inf'), float('-inf')]
    
    for char in token["chars"]:
        if current_char_idx < len(word_to_analyze) and char["c"] == word_to_analyze[current_char_idx]:
            c_bbox = char["bbox"]
            print(f"  Char '{char['c']}' BBox: {c_bbox}")
            
            # Check pixels in this char bbox
            x0, y0, x1, y1 = [int(c * zoom) for c in c_bbox]
            region = img_data[y0:y1, x0:x1]
            
            gray_region = np.mean(region, axis=2)
            content_mask = gray_region < 220 # Content pixels are dark
            
            if np.any(content_mask):
                rows = np.any(content_mask, axis=1)
                cols = np.any(content_mask, axis=0)
                rmin, rmax = np.where(rows)[0][[0, -1]]
                cmin, cmax = np.where(cols)[0][[0, -1]]
                
                actual_x0, actual_y0 = x0 + cmin, y0 + rmin
                actual_x1, actual_y1 = x0 + cmax, y0 + rmax
                
                print(f"    Glyph PDF: ({actual_x0/zoom}, {actual_y0/zoom}, {actual_x1/zoom}, {actual_y1/zoom})")
                
                word_glyph_bbox[0] = min(word_glyph_bbox[0], actual_x0/zoom)
                word_glyph_bbox[1] = min(word_glyph_bbox[1], actual_y0/zoom)
                word_glyph_bbox[2] = max(word_glyph_bbox[2], actual_x1/zoom)
                word_glyph_bbox[3] = max(word_glyph_bbox[3], actual_y1/zoom)
                
                # Visualize individual glyph box
                draw.rectangle([actual_x0, actual_y0, actual_x1, actual_y1], outline="blue", width=1)
            
            current_char_idx += 1

    print(f"\nSummary for word '{word_to_analyze}' in Title:")
    print(f"  PDF Span BBox Top Y: {bbox[1]:.2f}")
    print(f"  Actual Glyph Top Y:  {word_glyph_bbox[1]:.2f}")
    print(f"  Vertical Buffer Top:  {word_glyph_bbox[1] - bbox[1]:.2f} pts")
    
    # Check drawings (lines) near Title
    drawings = page.get_drawings()
    print(f"\nChecking drawings near Title Top (Y around {bbox[1]}):")
    for d in drawings:
        for item in d["items"]:
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                # Line within 10pts of title top
                if abs(p1.y - bbox[1]) < 10:
                    print(f"  Found line at Y={p1.y:.2f}: {p1} -> {p2}")
                    lx0, ly0, lx1, ly1 = int(p1.x*zoom), int(p1.y*zoom), int(p2.x*zoom), int(p2.y*zoom)
                    draw.line([lx0, ly0, lx1, ly1], fill="green", width=2)
            elif item[0] == "re": # rectangle
                r = item[1]
                if abs(r.y0 - bbox[1]) < 10 or abs(r.y1 - bbox[1]) < 10:
                    print(f"  Found drawing rect near title: {r}")

    debug_path = "tool/READ/tmp/analyze_nerf_pixels.png"
    img.save(debug_path)
    print(f"\nDebug image saved to {debug_path}")

if __name__ == "__main__":
    pdf = "tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    analyze_token_pixels(pdf, 0, "NeRF")
