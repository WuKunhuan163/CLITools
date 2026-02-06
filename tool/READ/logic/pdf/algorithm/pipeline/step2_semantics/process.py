import json
from pathlib import Path
from PIL import Image, ImageDraw
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

    def process(self, tokens: List[Dict[str, Any]], output_dir: Path, zoom: float, background_img: Image.Image = None) -> List[Dict[str, Any]]:
        # --- Visualization Refactoring ---
        from .viz_helper import VizHelper
        vh = VizHelper(str(self.project_root), self.font_dir)
        
        # 1. Initial PDF Reconstruction (Stage 1 status)
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="1_initial_status_reproduced")
        
        # 2. Layout Analysis (Recursive Slicing)
        from .layout import LayoutAnalyzer
        la = LayoutAnalyzer(self.median_size)
        
        # Perform Recursive Slicing Analysis
        separators, ordered_tokens = la.analyze(tokens, self.page_width*zoom, self.page_height*zoom)
        
        # 2.1 Separator Analysis (Colored separators, zones, background text)
        # Use the perfect PDF background instead of PIL rendering
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="2.1_separator_analysis", exclude_lines=False)
        # Add analysis overlays on top of the reproduced image
        viz_21_img = Image.open(output_dir / "2.1_separator_analysis.png").convert("RGBA")
        draw_21 = ImageDraw.Draw(viz_21_img)
        # Zones
        for zone in la.zones: draw_21.rectangle(zone["bbox"], fill=(200, 200, 200, 100))
        # Separators (all, colored)
        vh.render_separators(draw_21, separators, only_order_changing=False)
        viz_21_img.save(output_dir / "2.1_separator_analysis.png")
        
        # 2.2 Separator Reproduction (High quality PDF-based background + black separators)
        active_seps = [s for s in separators if s.get("order_changing")]
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="2.2_separator_reproduced", 
                            exclude_lines=True, separators=active_seps, draw_text_bbox=False, fill_text_bbox=False)
        
        # 3.0 Token Glyph Info (Light green shading for tokens)
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="3.0_token_glyph_info", 
                            exclude_lines=True, draw_text_bbox=False, fill_text_bbox=True)
        
        # 3.1 Line & Block Info Visualization (Background text + outlines)
        # For 3.1, we also want the light green shading for tokens
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="3.1_line_block_info", 
                            exclude_lines=True, fill_text_bbox=True)
        viz_31_img = Image.open(output_dir / "3.1_line_block_info.png").convert("RGBA")
        draw_31 = ImageDraw.Draw(viz_31_img)
        # Line & Block outlines (using PIL draw on top of shaded PDF)
        vh.render_line_block_info(draw_31, tokens)
        # Active separators (black)
        vh.render_separators(draw_31, active_seps, only_order_changing=True)
        viz_31_img.save(output_dir / "3.1_line_block_info.png")
        
        # Save analysis data
        analysis_data = {
            "page_width": self.page_width,
            "page_height": self.page_height,
            "zoom": zoom,
            "separators": separators
        }
        with open(output_dir / "analysis.json", "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
        # 3. Return ordered tokens as semantic items
        semantic_items = []
        for tk in ordered_tokens:
            if tk["type"] == "text":
                semantic_items.append({
                    "type": "paragraph", "bbox": [c / zoom for c in tk["bbox"]],
                    "text": tk["text"], "md_text": tk["text"]
                })
        return semantic_items
