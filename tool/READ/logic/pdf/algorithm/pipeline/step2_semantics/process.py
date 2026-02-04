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
        Reproduces the PDF layout using Stage 1 tokens and glyph bboxes.
        """
        pdf = FPDF(unit="pt", format=[self.page_width, self.page_height])
        pdf.set_auto_page_break(auto=False)
        pdf.add_page()
        
        # Register Arial variants as default fallback
        arial_variants = {"": "arial", "B": "arial-bold", "I": "arial-italic", "BI": "arial-bold-italic"}
        for style, name in arial_variants.items():
            p = self.font_dir / name / "font.ttf"
            if p.exists(): pdf.add_font("Arial", style, str(p))
        
        # Cache for registered fonts: {family: [styles]}
        registered_fonts = {"Arial": list(arial_variants.keys())}
        
        from tool.FONT.logic.engine import FontManager
        fm = FontManager(self.project_root)

        for tk in tokens:
            bbox = [c / zoom for c in tk.get("glyph_bbox", tk["bbox"])]
            
            if tk["type"] == "text":
                raw_font = tk.get("font", "Arial")
                style = ""
                if tk.get("flags", 0) & 2: style += "I" # Italic
                if tk.get("flags", 0) & 16: style += "B" # Bold
                
                norm_family = fm.normalize_name(raw_font)
                
                # Special mapping for common font name variations and fallbacks
                if norm_family == "arnhem-black": norm_family = "arnhem-bold"
                if norm_family == "arnhem-normal": norm_family = "arnhem-blond"
                
                if norm_family not in registered_fonts:
                    variants_found = []
                    # 1. Regular
                    p = self.font_dir / norm_family / "font.ttf"
                    if p.exists():
                        pdf.add_font(norm_family, "", str(p))
                        variants_found.append("")
                        # If the font name itself implies bold or italic, register it as that variant too
                        if "bold" in norm_family:
                            pdf.add_font(norm_family, "B", str(p))
                            variants_found.append("B")
                        if "italic" in norm_family or "oblique" in norm_family:
                            pdf.add_font(norm_family, "I", str(p))
                            variants_found.append("I")
                        if ("bold" in norm_family) and ("italic" in norm_family or "oblique" in norm_family):
                            pdf.add_font(norm_family, "BI", str(p))
                            variants_found.append("BI")
                    
                    # 2. Bold (if not already found)
                    if "B" not in variants_found:
                        p_bold = self.font_dir / f"{norm_family}-bold" / "font.ttf"
                        if not p_bold.exists() and "-blond" in norm_family:
                            p_bold = self.font_dir / norm_family.replace("-blond", "-bold") / "font.ttf"
                        if not p_bold.exists() and "-book" in norm_family:
                            p_bold = self.font_dir / norm_family.replace("-book", "-bold") / "font.ttf"
                        if p_bold.exists(): pdf.add_font(norm_family, "B", str(p_bold)); variants_found.append("B")
                    
                    # 3. Italic (if not already found)
                    if "I" not in variants_found:
                        p_italic = self.font_dir / f"{norm_family}-italic" / "font.ttf"
                        if not p_italic.exists() and "-blond" in norm_family:
                            p_italic = self.font_dir / norm_family.replace("-blond", "-blonditalic") / "font.ttf"
                        if p_italic.exists(): pdf.add_font(norm_family, "I", str(p_italic)); variants_found.append("I")
                    
                    # 4. Bold Italic (if not already found)
                    if "BI" not in variants_found:
                        p_bi = self.font_dir / f"{norm_family}-bold-italic" / "font.ttf"
                        if not p_bi.exists() and "-blond" in norm_family:
                            p_bi = self.font_dir / norm_family.replace("-blond", "-bolditalic") / "font.ttf"
                        if not p_bi.exists():
                            # Try to find any bold variant to use as fallback
                            if "B" in variants_found:
                                # We already registered it as "B", but fpdf2 needs it registered as "BI" too
                                # We'll do this below
                                pass
                        
                        if p_bi and p_bi.exists():
                            pdf.add_font(norm_family, "BI", str(p_bi))
                            variants_found.append("BI")
                        elif "B" in variants_found:
                            # Fallback BI to B if BI is missing but B exists
                            # We need the path again
                            p_fallback = self.font_dir / f"{norm_family}-bold" / "font.ttf"
                            if not p_fallback.exists() and "-blond" in norm_family:
                                p_fallback = self.font_dir / norm_family.replace("-blond", "-bold") / "font.ttf"
                            if not p_fallback.exists():
                                p_fallback = self.font_dir / norm_family / "font.ttf" # Last resort
                            
                            if p_fallback.exists():
                                pdf.add_font(norm_family, "BI", str(p_fallback))
                                variants_found.append("BI")
                    
                    if variants_found: registered_fonts[norm_family] = variants_found
                    else:
                        p = fm.get_font_path(raw_font)
                        if p and Path(p).exists(): pdf.add_font(norm_family, "", p); registered_fonts[norm_family] = [""]
                        else: registered_fonts[norm_family] = []

                if norm_family in registered_fonts and registered_fonts[norm_family]:
                    font_to_use = norm_family
                    style_to_use = style if style in registered_fonts[norm_family] else ""
                else:
                    font_to_use = "Arial"
                    style_to_use = style if style in registered_fonts["Arial"] else ""

                try:
                    pdf.set_font(font_to_use, style=style_to_use, size=tk.get("size", 10))
                except:
                    pdf.set_font("Arial", style=style_to_use, size=tk.get("size", 10))
                
                color = tk.get("color", 0)
                r, g, b = (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF
                pdf.set_text_color(r, g, b)
                pdf.set_xy(bbox[0], bbox[1])
                try:
                    pdf.cell(w=bbox[2]-bbox[0], h=bbox[3]-bbox[1], text=tk["text"], border=0)
                except:
                    clean_text = "".join([c if ord(c) < 256 else "?" for c in tk["text"]])
                    try: pdf.cell(w=bbox[2]-bbox[0], h=bbox[3]-bbox[1], text=clean_text, border=0)
                    except: pass
            
            elif tk["type"] == "visual":
                v_bbox = [c / zoom for c in tk["bbox"]]
                # Try to embed the merged image token if it exists
                token_img_path = output_dir.parent / "step1_tokenization" / "7_merged_image_tokens" / f"{tk['id']}.png"
                if token_img_path.exists():
                    try:
                        pdf.image(str(token_img_path), x=v_bbox[0], y=v_bbox[1], w=v_bbox[2]-v_bbox[0], h=v_bbox[3]-v_bbox[1])
                    except Exception as e:
                        print(f"Warning: Failed to embed image token {tk['id']} into PDF: {e}")
                        pdf.set_draw_color(200, 200, 200)
                        pdf.rect(v_bbox[0], v_bbox[1], v_bbox[2]-v_bbox[0], v_bbox[3]-v_bbox[1])
                else:
                    pdf.set_draw_color(200, 200, 200)
                    pdf.rect(v_bbox[0], v_bbox[1], v_bbox[2]-v_bbox[0], v_bbox[3]-v_bbox[1])

        pdf_output_path = output_dir / "1_initial_status_reproduced.pdf"
        pdf.output(str(pdf_output_path))
        
        # Render to PNG for verification
        import fitz
        doc = fitz.open(str(pdf_output_path))
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(str(output_dir / "1_initial_status_reproduced.png"))
        doc.close()
