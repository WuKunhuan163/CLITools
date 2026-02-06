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
        # Very basic PIL font loading logic
        # For better results, we should use the same normalization as in FPDF
        from tool.FONT.logic.engine import FontManager
        fm = FontManager(self.project_root)
        norm_name = fm.normalize_name(font_name)
        
        cache_key = (norm_name, size)
        if cache_key in self.font_cache: return self.font_cache[cache_key]
        
        font_path = self.font_dir / norm_name / "font.ttf"
        if not font_path.exists():
            # Fallback
            font_path = self.font_dir / "arial" / "font.ttf"
            
        try:
            font = ImageFont.truetype(str(font_path), int(round(size)))
        except:
            font = ImageFont.load_default()
            
        self.font_cache[cache_key] = font
        return font

    def render_tokens(self, draw: ImageDraw.Draw, tokens: List[Dict[str, Any]], draw_text: bool = True, draw_bbox: bool = True, bbox_alpha: int = 60):
        """
        Draws text and visual tokens.
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
        Draws separators.
        """
        for s in separators:
            if only_order_changing and not s.get("order_changing"): continue
            
            bbox = s["bbox"]
            color = (255, 0, 0, 255) if s.get("order_changing") else (0, 0, 255, 255)
            # Draw as a slightly thicker line if it's a separator analysis view, 
            # or thin black line if it's reproduction. 
            # Actually, let's make it configurable or handle it via color.
            draw.line([bbox[0], bbox[1], bbox[2], bbox[3]], fill=color if not only_order_changing else (0,0,0,255), width=1 if only_order_changing else 3)
            if not only_order_changing:
                draw.text((bbox[0] + 5, bbox[1] + 5), s["id"], fill=color)

    def render_line_block_info(self, draw: ImageDraw.Draw, tokens: List[Dict[str, Any]]):
        """
        Draws line and block outlines.
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

