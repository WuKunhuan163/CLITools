import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Tuple, Optional

class VizHelper:
    def __init__(self, project_root: str, font_dir: Path):
        self.project_root = Path(project_root)
        self.font_dir = font_dir
        self.font_cache = {}

    def get_pil_font(self, font_name: str, size: float):
        # Basic PIL font loading logic
        from tool.FONT.logic.engine import FontManager
        fm = FontManager(self.project_root)
        norm_name = fm.normalize_name(font_name)
        
        cache_key = (norm_name, size)
        if cache_key in self.font_cache: return self.font_cache[cache_key]
        
        font_path = self.font_dir / norm_name / "font.ttf"
        if not font_path.exists():
            font_path = self.font_dir / "arial" / "font.ttf"
            
        try:
            font = ImageFont.truetype(str(font_path), int(round(size)))
        except:
            font = ImageFont.load_default()
            
        self.font_cache[cache_key] = font
        return font

    def render_tokens(self, draw: ImageDraw.Draw, tokens: List[Dict[str, Any]], draw_text: bool = True, draw_bbox: bool = True, bbox_alpha: int = 60):
        """
        Draws text and visual tokens using PIL.
        """
        for t in tokens:
            if t.get("is_absorbed"): continue
            if t.get("subtype") in ["line", "rect"]: continue
            
            tb = t.get("glyph_bbox", t["bbox"])
            if t["type"] == "text":
                if draw_bbox:
                    draw.rectangle(tb, outline=(0, 255, 0, bbox_alpha), width=1)
                if draw_text:
                    font = self.get_pil_font(t.get("font", "Arial"), t.get("size", 10))
                    color = t.get("color", 0)
                    r, g, b = (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF
                    draw.text((tb[0], tb[1]), t["text"], fill=(r, g, b, 255), font=font)
            else:
                if draw_bbox:
                    draw.rectangle(tb, outline=(0, 0, 255, bbox_alpha), width=1)
                    draw.text((tb[0]+2, tb[1]+2), t["id"], fill=(0, 0, 255, 100))

    def render_separators(self, draw: ImageDraw.Draw, separators: List[Dict[str, Any]], only_order_changing: bool = True):
        """
        Draws separators using PIL.
        """
        for s in separators:
            if only_order_changing and not s.get("order_changing"): continue
            
            bbox = s["bbox"]
            is_oc = s.get("order_changing")
            
            if only_order_changing:
                # Reproduction style: thin black line
                color = (0, 0, 0, 255)
                width = 1
            else:
                # Analysis style: thick colored line
                color = (255, 0, 0, 255) if is_oc else (0, 0, 255, 255)
                width = 3
                
            draw.line([bbox[0], bbox[1], bbox[2], bbox[3]], fill=color, width=width)
            
            if not only_order_changing:
                # Add label for analysis
                draw.text((bbox[0] + 5, bbox[1] + 5), s["id"], fill=color)

    def render_line_block_info(self, draw: ImageDraw.Draw, tokens: List[Dict[str, Any]]):
        """
        Draws line and block outlines using PIL.
        """
        blocks = {}
        for t in tokens:
            if t.get("is_absorbed"): continue
            if t.get("subtype") in ["line", "rect"]: continue
            if t["type"] == "text":
                bid, lid = t.get("block_id"), t.get("line_id")
                if bid is not None and lid is not None:
                    if bid not in blocks: blocks[bid] = {}
                    if lid not in blocks[bid]: blocks[bid][lid] = []
                    blocks[bid][lid].append(t)

        # Draw Lines (Darker Green)
        for bid, lines in blocks.items():
            for lid, tkns in lines.items():
                if not tkns: continue
                lx0 = min(t.get("glyph_bbox", t["bbox"])[0] for t in tkns)
                ly0 = min(t.get("glyph_bbox", t["bbox"])[1] for t in tkns)
                lx1 = max(t.get("glyph_bbox", t["bbox"])[2] for t in tkns)
                ly1 = max(t.get("glyph_bbox", t["bbox"])[3] for t in tkns)
                draw.rectangle([lx0, ly0, lx1, ly1], outline=(0, 128, 0, 150), width=1)
                
        # Draw Blocks (Blue)
        for bid, lines in blocks.items():
            all_tkns = [t for l in lines.values() for t in l]
            if not all_tkns: continue
            bx0 = min(t.get("glyph_bbox", t["bbox"])[0] for t in all_tkns)
            by0 = min(t.get("glyph_bbox", t["bbox"])[1] for t in all_tkns)
            bx1 = max(t.get("glyph_bbox", t["bbox"])[2] for t in all_tkns)
            by1 = max(t.get("glyph_bbox", t["bbox"])[3] for t in all_tkns)
            draw.rectangle([bx0-2, by0-2, bx1+2, by1+2], outline=(0, 0, 255, 150), width=1)

    def reproduce_to_pdf(self, tokens: List[Dict[str, Any]], output_dir: Path, zoom: float, page_width: float, page_height: float, name: str, exclude_lines: bool = False, separators: List[Dict[str, Any]] = None, draw_text_bbox: bool = False):
        """
        Reproduces the PDF layout using Stage 1 tokens and glyph bboxes via FPDF.
        Then renders to PNG for high-quality background.
        """
        from fpdf import FPDF
        pdf = FPDF(unit="pt", format=[page_width, page_height])
        pdf.set_auto_page_break(auto=False)
        pdf.add_page()
        
        # Register fonts
        arial_variants = {"": "arial", "B": "arial-bold", "I": "arial-italic", "BI": "arial-bold-italic"}
        for style, name_v in arial_variants.items():
            p = self.font_dir / name_v / "font.ttf"
            if p.exists(): pdf.add_font("Arial", style, str(p))
        registered_fonts = {"Arial": list(arial_variants.keys())}
        
        from tool.FONT.logic.engine import FontManager
        fm = FontManager(self.project_root)

        # 1. Render Visual Tokens
        for tk in tokens:
            if tk["type"] == "visual":
                if exclude_lines and tk.get("subtype") in ["line", "rect"]: continue
                
                v_bbox = [c / zoom for c in tk["bbox"]]
                token_img_path = output_dir.parent / "step1_tokenization" / "7_merged_image_tokens" / f"{tk['id']}.png"
                if token_img_path.exists():
                    try:
                        pdf.image(str(token_img_path), x=v_bbox[0], y=v_bbox[1], w=v_bbox[2]-v_bbox[0], h=v_bbox[3]-v_bbox[1])
                    except:
                        pdf.set_draw_color(200, 200, 200); pdf.rect(v_bbox[0], v_bbox[1], v_bbox[2]-v_bbox[0], v_bbox[3]-v_bbox[1])
                else:
                    pdf.set_draw_color(200, 200, 200); pdf.rect(v_bbox[0], v_bbox[1], v_bbox[2]-v_bbox[0], v_bbox[3]-v_bbox[1])

        # 2. Render Text Tokens
        for tk in tokens:
            if tk["type"] == "text" and not tk.get("is_absorbed"):
                bbox = [c / zoom for c in tk.get("glyph_bbox", tk["bbox"])]
                raw_font = tk.get("font", "Arial")
                style = ""
                if tk.get("flags", 0) & 2: style += "I"
                if tk.get("flags", 0) & 16: style += "B"
                
                norm_family = fm.normalize_name(raw_font)
                if norm_family == "arnhem-black": norm_family = "arnhem-bold"
                if norm_family == "arnhem-normal": norm_family = "arnhem-blond"
                
                if norm_family not in registered_fonts:
                    variants = []
                    # Simple registration logic
                    for s, suffix in [("", ""), ("B", "-bold"), ("I", "-italic"), ("BI", "-bold-italic")]:
                        p = self.font_dir / (norm_family + suffix) / "font.ttf"
                        if p.exists(): 
                            try:
                                pdf.add_font(norm_family, s, str(p))
                                variants.append(s)
                            except: pass
                    registered_fonts[norm_family] = variants

                font_to_use = norm_family if (norm_family in registered_fonts and registered_fonts[norm_family]) else "Arial"
                style_to_use = style if style in registered_fonts.get(font_to_use, []) else ""
                
                try: pdf.set_font(font_to_use, style=style_to_use, size=tk.get("size", 10))
                except: pdf.set_font("Arial", style=style_to_use, size=tk.get("size", 10))
                
                color = tk.get("color", 0)
                pdf.set_text_color((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)
                pdf.set_xy(bbox[0], bbox[1])
                
                try: pdf.cell(w=bbox[2]-bbox[0], h=bbox[3]-bbox[1], text=tk["text"], border=1 if draw_text_bbox else 0)
                except:
                    clean_text = "".join([c if ord(c) < 256 else "?" for c in tk["text"]])
                    try: pdf.cell(w=bbox[2]-bbox[0], h=bbox[3]-bbox[1], text=clean_text, border=1 if draw_text_bbox else 0)
                    except: pass
                    
        # 3. Render Separators
        if separators:
            pdf.set_draw_color(0, 0, 0)
            pdf.set_line_width(0.5)
            for s in separators:
                # Separators in analysis are already zoomed
                s_bbox = [c / zoom for c in s["bbox"]]
                pdf.line(s_bbox[0], s_bbox[1], s_bbox[2], s_bbox[3])

        pdf_output_path = output_dir / f"{name}.pdf"
        pdf.output(str(pdf_output_path))
        
        import fitz
        doc = fitz.open(str(pdf_output_path))
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(str(output_dir / f"{name}.png"))
        doc.close()
