import json
from pathlib import Path
from fpdf import FPDF
from PIL import Image
import numpy as np
from typing import List, Dict, Any, Tuple

class SemanticsEngine:
    """
    Handles semantic tagging, logical block merging, and final output generation.
    Incorporates layout analysis and PDF reconstruction.
    """
    def __init__(self, page_rect: Any, median_size: float, project_root: str):
        self.page_rect = page_rect
        self.page_width = page_rect.width
        self.page_height = page_rect.height
        self.median_size = median_size
        self.project_root = Path(project_root)
        self.font_dir = self.project_root / "resource" / "tool" / "FONT" / "data" / "install"

    def process(self, tokens: List[Dict[str, Any]], output_dir: Path, zoom: float) -> List[Dict[str, Any]]:
        # 1. Initial PDF Reconstruction
        self.reproduce_initial_pdf(tokens, output_dir, zoom)
        
        # 2. Return tokens as semantic items for now to avoid empty output
        semantic_items = []
        for tk in tokens:
            if tk["type"] == "text":
                semantic_items.append({
                    "type": "paragraph", "bbox": [c / zoom for c in tk["bbox"]],
                    "text": tk["text"], "md_text": tk["text"]
                })
        return semantic_items

    def reproduce_initial_pdf(self, tokens: List[Dict[str, Any]], output_dir: Path, zoom: float):
        """
        Reproduces the PDF layout using Stage 1 tokens.
        """
        pdf = FPDF(unit="pt", format=[self.page_width, self.page_height])
        pdf.add_page()
        
        # Register Arial variants
        arial_path = self.font_dir / "arial" / "font.ttf"
        arial_b_path = self.font_dir / "arial-bold" / "font.ttf"
        arial_i_path = self.font_dir / "arial-italic" / "font.ttf"
        arial_bi_path = self.font_dir / "arial-bold-italic" / "font.ttf"
        
        if arial_path.exists(): pdf.add_font("Arial", "", str(arial_path))
        if arial_b_path.exists(): pdf.add_font("Arial", "B", str(arial_b_path))
        if arial_i_path.exists(): pdf.add_font("Arial", "I", str(arial_i_path))
        if arial_bi_path.exists(): pdf.add_font("Arial", "BI", str(arial_bi_path))
        
        # Register Helvetica
        helvetica_path = self.font_dir / "helvetica" / "font.ttf"
        if helvetica_path.exists(): pdf.add_font("Helvetica", "", str(helvetica_path))
        
        pdf.set_font("Arial", size=10) # Default
        
        for tk in tokens:
            bbox = [c / zoom for c in tk["bbox"]] # Convert back to PDF points
            
            if tk["type"] == "text":
                # Set style
                style = ""
                if tk.get("flags", 0) & 2: style += "I" # Italic
                if tk.get("flags", 0) & 4: style += "B" # Bold
                
                # fpdf2 requires registering each style variant if it's a separate file
                # For now, we'll just use the base font and let fpdf2 try to synthesize or fallback
                try:
                    pdf.set_font("Arial", style=style, size=tk.get("size", 10))
                except:
                    pdf.set_font("Arial", style="", size=tk.get("size", 10))
                
                # Set color
                color = tk.get("color", 0)
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                pdf.set_text_color(r, g, b)
                
                # Position and write text
                pdf.set_xy(bbox[0], bbox[1])
                try:
                    # Use a small width/height or the actual bbox
                    pdf.cell(w=bbox[2]-bbox[0], h=bbox[3]-bbox[1], text=tk["text"], border=0)
                except Exception as e:
                    # Fallback for unsupported characters: replace with '?'
                    clean_text = "".join([c if ord(c) < 256 else "?" for c in tk["text"]])
                    try:
                        pdf.cell(w=bbox[2]-bbox[0], h=bbox[3]-bbox[1], text=clean_text, border=0)
                    except: pass
                
            elif tk["type"] == "visual":
                # For now, just draw a rectangle or placeholder
                pdf.set_draw_color(200, 200, 200)
                pdf.rect(bbox[0], bbox[1], bbox[2]-bbox[0], bbox[3]-bbox[1])
                
        pdf_output_path = output_dir / "1_initial_status_reproduced.pdf"
        pdf.output(str(pdf_output_path))
        
        # Render to PNG for verification
        import fitz
        doc = fitz.open(str(pdf_output_path))
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(str(output_dir / "1_initial_status_reproduced.png"))
        doc.close()
