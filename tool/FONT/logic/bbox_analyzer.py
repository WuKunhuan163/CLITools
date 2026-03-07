import os
import sys
import json
import numpy as np
import fitz
from fpdf import FPDF
from PIL import Image, ImageDraw
from pathlib import Path

class BBoxAnalyzer:
    def __init__(self, font_path, output_dir, font_name=None):
        self.font_path = Path(font_path)
        self.output_dir = Path(output_dir)
        self.font_name = font_name or self.font_path.stem
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.zoom = 2.0

    def generate_source_pdf(self):
        """Generates a structured multi-page character table PDF."""
        pdf = FPDF()
        pdf.add_font(self.font_name, '', str(self.font_path))
        font_size = 34
        pdf.set_font(self.font_name, size=font_size)
        
        # Basic Latin (ASCII 33-126)
        chars = [chr(i) for i in range(33, 127)]
        
        cols = 10
        cell_w, cell_h = 18, 20
        x_start, y_start = 10, 20
        max_rows_per_page = 12
        
        pdf.add_page()
        current_row = 0
        
        for i, char in enumerate(chars):
            col = i % cols
            if i > 0 and col == 0:
                current_row += 1
                if current_row >= max_rows_per_page:
                    pdf.add_page()
                    current_row = 0
            
            pdf.set_xy(x_start + col * cell_w, y_start + current_row * cell_h)
            try:
                pdf.cell(cell_w, cell_h, char, border=0, align='C')
            except:
                pdf.cell(cell_w, cell_h, "?", border=0, align='C')
        
        pdf_path = self.output_dir / "source.pdf"
        pdf.output(str(pdf_path))
        return pdf_path

    def analyze(self, pdf_path):
        """Analyzes the PDF and generates visualizations/data."""
        doc = fitz.open(pdf_path)
        all_info = []
        glyph_images = []
        actual_images = []
        combined_images = []
        
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
            
            page_png_path = self.output_dir / f"temp_page_{page_idx}.png"
            pix.save(str(page_png_path))
            
            img = Image.open(page_png_path).convert("RGB")
            img_glyph = img.copy()
            img_actual = img.copy()
            img_combined = img.copy()
            draw_glyph = ImageDraw.Draw(img_glyph)
            draw_actual = ImageDraw.Draw(img_actual)
            draw_combined = ImageDraw.Draw(img_combined, "RGBA")
            
            raw = page.get_text("rawdict")
            
            for block in raw["blocks"]:
                if block["type"] == 0:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            f_size = span["size"]
                            for char_data in span["chars"]:
                                char = char_data["c"]
                                if char.isspace():
                                    continue
                                
                                bbox = [c * self.zoom for c in char_data["bbox"]]
                                
                                pad = 5
                                ix0, iy0, ix1, iy1 = [int(c) for c in bbox]
                                crop_x0, crop_y0 = max(0, ix0-pad), max(0, iy0-pad)
                                crop_x1, crop_y1 = min(img.width, ix1+pad), min(img.height, iy1+pad)
                                
                                if crop_x1 <= crop_x0 or crop_y1 <= crop_y0:
                                    continue
                                    
                                crop = img.crop((crop_x0, crop_y0, crop_x1, crop_y1))
                                mask = np.mean(np.array(crop), axis=2) < 200
                                
                                if not np.any(mask):
                                    continue

                                # Draw Glyph BBox
                                draw_glyph.rectangle(bbox, outline="red", width=1)
                                
                                rows = np.where(np.any(mask, axis=1))[0]
                                cols = np.where(np.any(mask, axis=0))[0]
                                ax0, ay0 = int(crop_x0 + cols[0]), int(crop_y0 + rows[0])
                                ax1, ay1 = int(crop_x0 + cols[-1]), int(crop_y0 + rows[-1])
                                actual_bbox = [ax0, ay0, ax1, ay1]
                                
                                # Draw Actual BBox
                                draw_actual.rectangle(actual_bbox, outline="blue", width=1)
                                
                                # Draw Combined (Glyph: light grey, Actual: blue)
                                draw_combined.rectangle(bbox, outline=(200, 200, 200, 150), width=1)
                                draw_combined.rectangle(actual_bbox, outline=(0, 0, 255, 255), width=1)
                                
                                normalized_heuristics = None
                                gw = bbox[2] - bbox[0]
                                gh = bbox[3] - bbox[1]
                                if gw > 0 and gh > 0:
                                    normalized_heuristics = [
                                        (actual_bbox[0] - bbox[0]) / gw,
                                        (actual_bbox[1] - bbox[1]) / gh,
                                        (actual_bbox[2] - bbox[0]) / gw,
                                        (actual_bbox[3] - bbox[1]) / gh
                                    ]
                                
                                all_info.append({
                                    "char": char,
                                    "page": page_idx,
                                    "glyph_bbox": [round(c, 2) for c in bbox],
                                    "actual_bbox": [round(c, 2) for c in actual_bbox],
                                    "heuristics": [round(c, 4) for c in normalized_heuristics] if normalized_heuristics else None,
                                    "font_size": f_size
                                })
            
            glyph_images.append(img_glyph)
            actual_images.append(img_actual)
            combined_images.append(img_combined)
            os.remove(page_png_path)
            
        total_width = glyph_images[0].width
        total_height = sum(img.height for img in glyph_images)
        final_glyph = Image.new("RGB", (total_width, total_height))
        final_actual = Image.new("RGB", (total_width, total_height))
        final_combined = Image.new("RGB", (total_width, total_height))
        
        y_offset = 0
        for g_img, a_img, c_img in zip(glyph_images, actual_images, combined_images):
            final_glyph.paste(g_img, (0, y_offset))
            final_actual.paste(a_img, (0, y_offset))
            final_combined.paste(c_img, (0, y_offset))
            y_offset += g_img.height
            
        final_glyph.save(str(self.output_dir / "glyph_bbox.png"))
        final_actual.save(str(self.output_dir / "actual_bbox.png"))
        final_combined.save(str(self.output_dir / "combined_bbox.png"))
        source_pix = doc[0].get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
        source_pix.save(str(self.output_dir / "source.png"))
        
        with open(self.output_dir / "info.json", 'w', encoding='utf-8') as f:
            json.dump(all_info, f, indent=2, ensure_ascii=False)
            
        heuristics_map = {}
        for item in all_info:
            if item["heuristics"]:
                heuristics_map[item["char"]] = item["heuristics"]
        
        with open(self.output_dir.parent / "info.json", 'w', encoding='utf-8') as f:
            json.dump({
                "font_name": self.font_name,
                "zoom": self.zoom,
                "heuristics": heuristics_map
            }, f, indent=2, ensure_ascii=False)
            
        return all_info

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    font_p = sys.argv[1]
    out_d = sys.argv[2]
    f_name = sys.argv[3] if len(sys.argv) > 3 else None
    analyzer = BBoxAnalyzer(font_p, out_d, f_name)
    pdf = analyzer.generate_source_pdf()
    analyzer.analyze(pdf)
