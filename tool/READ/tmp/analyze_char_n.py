import fitz
from PIL import Image, ImageDraw
import numpy as np
import os

def analyze_char_n(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    zoom = 10 # High zoom for detailed analysis
    
    # Find the title 'NeRF'
    blocks = page.get_text("rawdict")["blocks"]
    char_n = None
    for b in blocks:
        if b["type"] != 0: continue
        for line in b["lines"]:
            for span in line["spans"]:
                if "NeRF" in "".join([c["c"] for c in span["chars"]]):
                    for c in span["chars"]:
                        if c["c"] == "N":
                            char_n = c
                            break
                    if char_n: break
            if char_n: break
        if char_n: break

    if not char_n:
        print("Char 'N' not found in Title")
        return

    # Render the area
    bbox = char_n["bbox"]
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=bbox)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img_data = np.array(img)
    
    # Analyze vertical intensity profile
    gray = np.mean(img_data, axis=2)
    # Intensity is 0 (black) to 255 (white)
    # We want to see how "dark" each row is
    v_profile = 255 - np.mean(gray, axis=1) # High value means darker row
    
    print(f"Char 'N' Analysis (Zoom {zoom}):")
    print(f"BBox: {bbox}")
    print(f"Image Size: {pix.width}x{pix.height}")
    
    # Find where the character actually is
    mask = gray < 200
    if np.any(mask):
        rows = np.where(np.any(mask, axis=1))[0]
        print(f"Dark pixels row range: {rows[0]} to {rows[-1]}")
        print(f"Relative Top: {rows[0] / (pix.height)} of bbox height")
        print(f"Relative Bottom: {rows[-1] / (pix.height)} of bbox height")
        
        # Check the top few rows for the line
        # If the line at 54.6 is present, it should be at row: (54.6 - 51.28) * zoom = 3.32 * 10 = 33
        # Wait, the clip starts at 51.28.
        line_y_expected = (54.60 - 51.28) * zoom
        print(f"Expected Line Row (if present): ~{line_y_expected}")
        
    img.save("tool/READ/tmp/char_n_crop.png")
    
    # Save a plot-like representation of the profile
    profile_img = Image.new("RGB", (200, pix.height), (255, 255, 255))
    p_draw = ImageDraw.Draw(profile_img)
    for y, val in enumerate(v_profile):
        p_draw.line([(0, y), (val, y)], fill=(255, 0, 0))
    profile_img.save("tool/READ/tmp/char_n_profile.png")
    
    print("\nResults saved to tool/READ/tmp/char_n_crop.png and char_n_profile.png")

if __name__ == "__main__":
    pdf = "tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    analyze_char_n(pdf, 0)


