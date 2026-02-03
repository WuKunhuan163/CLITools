import fitz
import json
import os
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path

def analyze_font_heuristics():
    pdf_path = "/Applications/AITerminalTools/tmp/source.pdf"
    png_path = "/Applications/AITerminalTools/tmp/source.png"
    font_dir = "/Applications/AITerminalTools/resource/fonts/arnhem-blond"
    output_json = os.path.join(font_dir, "heuristics.json")
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    raw = page.get_text("rawdict")
    zoom = 2.0
    
    img = Image.open(png_path).convert("RGB")
    img_glyph = img.copy()
    img_actual = img.copy()
    draw_glyph = ImageDraw.Draw(img_glyph)
    draw_actual = ImageDraw.Draw(img_actual)
    
    heuristics = {}
    
    for block in raw["blocks"]:
        if block["type"] != 0: continue
        for line in block["lines"]:
            for span in line["spans"]:
                font_size = span["size"]
                for char_data in span["chars"]:
                    char = char_data["c"]
                    bbox = char_data["bbox"]
                    x0, y0, x1, y1 = [c * zoom for c in bbox]
                    
                    draw_glyph.rectangle([x0, y0, x1, y1], outline="red", width=1)
                    
                    # Actual Pixel Analysis
                    pad = 5
                    ix0, iy0, ix1, iy1 = int(x0), int(y0), int(x1), int(y1)
                    crop_x0, crop_y0 = max(0, ix0-pad), max(0, iy0-pad)
                    crop_x1, crop_y1 = min(img.width, ix1+pad), min(img.height, iy1+pad)
                    
                    crop = img.crop((crop_x0, crop_y0, crop_x1, crop_y1))
                    mask = np.mean(np.array(crop), axis=2) < 200
                    
                    if np.any(mask):
                        rows = np.where(np.any(mask, axis=1))[0]
                        cols = np.where(np.any(mask, axis=0))[0]
                        
                        ax0, ay0 = crop_x0 + cols[0], crop_y0 + rows[0]
                        ax1, ay1 = crop_x0 + cols[-1], crop_y0 + rows[-1]
                        
                        draw_actual.rectangle([ax0, ay0, ax1, ay1], outline="blue", width=1)
                        
                        # Calculate normalized offsets
                        # Based on user: relative to Glyph normalized (0..1)
                        # We use font_size * zoom as the unit
                        norm_unit = font_size * zoom
                        heuristics[char] = {
                            "left": round((ax0 - x0) / norm_unit, 4),
                            "top": round((ay0 - y0) / norm_unit, 4),
                            "right": round((ax1 - x1) / norm_unit, 4),
                            "bottom": round((ay1 - y1) / norm_unit, 4)
                        }
    
    img_glyph.save("/Applications/AITerminalTools/tmp/glyph_bbox.png")
    img_actual.save("/Applications/AITerminalTools/tmp/actual_bbox.png")
    
    with open(output_json, 'w') as f:
        json.dump(heuristics, f, indent=2)
    
    print(f"Heuristics saved to {output_json}")
    print(f"Visualizations saved to /Applications/AITerminalTools/tmp/glyph_bbox.png and actual_bbox.png")

if __name__ == "__main__":
    analyze_font_heuristics()
