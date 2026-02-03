import os
import sys
import re
import json
import numpy as np
import fitz
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_source_pdf(font_path, output_pdf):
    """Generates a structured character table PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Arnhem-Blond', '', font_path)
    font_size = 34
    pdf.set_font('Arnhem-Blond', size=font_size)
    
    chars = "".join([chr(i) for i in range(33, 127)])
    cols = 10
    cell_w, cell_h = 18, 20
    x_start, y_start = 10, 20
    
    for i, char in enumerate(chars):
        row, col = i // cols, i % cols
        pdf.set_xy(x_start + col * cell_w, y_start + row * cell_h)
        pdf.cell(cell_w, cell_h, char, border=0, align='C')
        
    pdf.output(output_pdf)
    print(f"Generated {output_pdf}")

def analyze_and_draw(pdf_path, font_path, base_dir):
    """Analyzes the PDF and generates visualizations/data."""
    # Render PDF to PNG at zoom 2.0
    doc = fitz.open(pdf_path)
    page = doc[0]
    zoom = 2.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    source_png = os.path.join(base_dir, "source.png")
    pix.save(source_png)
    
    img = Image.open(source_png).convert("RGB")
    img_glyph = img.copy()
    img_actual = img.copy()
    draw_glyph = ImageDraw.Draw(img_glyph)
    draw_actual = ImageDraw.Draw(img_actual)
    
    raw = page.get_text("rawdict")
    info = []
    
    for block in raw["blocks"]:
        # Record all blocks to see what the "strange" ones are
        b_bbox = [c * zoom for c in block["bbox"]]
        b_type = block["type"]
        
        # REMOVED: draw_glyph.rectangle(b_bbox, outline="green", width=1)
        
        if b_type == 0: # Text block
            for line in block["lines"]:
                l_bbox = [c * zoom for c in line["bbox"]]
                # REMOVED: draw_glyph.rectangle(l_bbox, outline="yellow", width=1)
                
                for span in line["spans"]:
                    font_size = span["size"]
                    for char_data in span["chars"]:
                        char = char_data["c"]
                        bbox = [c * zoom for c in char_data["bbox"]]
                        
                        # Theoretical Glyph BBox
                        draw_glyph.rectangle(bbox, outline="red", width=1)
                        
                        # Actual Pixel Analysis
                        pad = 5
                        ix0, iy0, ix1, iy1 = [int(c) for c in bbox]
                        crop_x0, crop_y0 = max(0, ix0-pad), max(0, iy0-pad)
                        crop_x1, crop_y1 = min(img.width, ix1+pad), min(img.height, iy1+pad)
                        
                        crop = img.crop((crop_x0, crop_y0, crop_x1, crop_y1))
                        mask = np.mean(np.array(crop), axis=2) < 200
                        
                        actual_bbox = None
                        if np.any(mask):
                            rows = np.where(np.any(mask, axis=1))[0]
                            cols = np.where(np.any(mask, axis=0))[0]
                            ax0, ay0 = int(crop_x0 + cols[0]), int(crop_y0 + rows[0])
                            ax1, ay1 = int(crop_x0 + cols[-1]), int(crop_y0 + rows[-1])
                            actual_bbox = [ax0, ay0, ax1, ay1]
                            draw_actual.rectangle(actual_bbox, outline="blue", width=1)
                        
                        info.append({
                            "char": char,
                            "glyph_bbox": [round(c, 2) for c in bbox],
                            "actual_bbox": [round(c, 2) for c in actual_bbox] if actual_bbox else None,
                            "font_size": font_size,
                            "type": "character"
                        })
        else:
            info.append({
                "type": "non-text-block",
                "block_type": b_type,
                "glyph_bbox": [round(c, 2) for c in b_bbox]
            })

    img_glyph.save(os.path.join(base_dir, "glyph_bbox.png"))
    img_actual.save(os.path.join(base_dir, "actual_bbox.png"))
    
    with open(os.path.join(base_dir, "info.json"), 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"Analysis complete. Results in {base_dir}")

if __name__ == "__main__":
    base = "/Applications/AITerminalTools/tmp/arnhem-blond_bbox"
    font = os.path.join(base, "arnhem-blond.ttf")
    pdf = os.path.join(base, "source.pdf")
    
    create_source_pdf(font, pdf)
    analyze_and_draw(pdf, font, base)

