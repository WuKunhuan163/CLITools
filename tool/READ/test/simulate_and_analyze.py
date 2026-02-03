import fitz
from PIL import Image, ImageDraw
import numpy as np
import os

def run_simulation():
    os.makedirs("tool/READ/tmp", exist_ok=True)
    pdf_path = "tool/READ/test/simulate_line_text.pdf"
    doc = fitz.open()
    page = doc.new_page()
    
    # 1. Draw line at 54.6
    # Drawing a line across the page
    shape = page.new_shape()
    shape.draw_line(fitz.Point(40, 54.6), fitz.Point(500, 54.6))
    shape.finish(color=(0, 0, 0), width=0.4)
    shape.commit()
    
    # 2. Insert text 'NeRF'
    # To get BBox Top at 51.28 with Helvetica (ascender in fitz is ~0.718)
    # Origin = 51.28 + (34 * 0.718) = 75.69
    # We use a standard font like 'helv'
    font_size = 34.0
    # We'll use insert_text which is simpler for simulation
    page.insert_text((41.75, 75.69), "NeRF: Representing Scenes", fontname="helv", fontsize=font_size)
    
    doc.save(pdf_path)
    doc.close()
    
    # 3. Analyze
    doc = fitz.open(pdf_path)
    page = doc[0]
    zoom = 8 # High zoom for 0.1pt precision
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img_data = np.array(img)
    draw = ImageDraw.Draw(img)
    
    # Get text metadata
    blocks = page.get_text("rawdict")["blocks"]
    if not blocks:
        print("No text found in simulated PDF!")
        return
        
    span = blocks[0]["lines"][0]["spans"][0]
    print(f"Simulated Span BBox: {span['bbox']}")
    print(f"Simulated Ascender: {span['ascender']}")
    
    # Draw character bboxes (Red) and analyze content
    for char in span["chars"]:
        c_bbox = char["bbox"]
        cx0, cy0, cx1, cy1 = [int(c * zoom) for c in c_bbox]
        draw.rectangle([cx0, cy0, cx1, cy1], outline="red", width=1)
        
        # Analyze pixels in char box
        region = img_data[cy0:cy1, cx0:cx1]
        mask = np.mean(region, axis=2) < 220
        if np.any(mask):
            rows = np.where(np.any(mask, axis=1))[0]
            actual_y0 = cy0 + rows[0]
            print(f"  Char '{char['c']}' Content Top PDF: {actual_y0/zoom:.2f}")

    # Detect lines (Green)
    for d in page.get_drawings():
        for item in d["items"]:
            if item[0] == "l":
                ly = item[1].y
                print(f"  Line Y (Drawing): {ly:.2f}")
                draw.line([0, ly*zoom, pix.width, ly*zoom], fill="green", width=1)

    img_path = "tool/READ/tmp/simulate_and_analyze.png"
    img.save(img_path)
    doc.close()
    print(f"\nSimulation complete. Result saved to {img_path}")

if __name__ == "__main__":
    run_simulation()


