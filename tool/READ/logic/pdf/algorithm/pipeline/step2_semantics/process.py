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
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="1_initial_status_reproduced", keep_pdf=True)
        
        # 2. Layout Analysis (Recursive Slicing)
        from .layout import LayoutAnalyzer
        la = LayoutAnalyzer(self.median_size)
        
        # Perform Recursive Slicing Analysis
        separators, ordered_tokens, unbroken_block_ids = la.analyze(tokens, self.page_width*zoom, self.page_height*zoom)
        
        # 2.1 Separator Analysis (Colored separators, zones, background text)
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="2.1_separator_analysis", exclude_lines=False, keep_pdf=False)
        viz_21_img = Image.open(output_dir / "2.1_separator_analysis.png").convert("RGBA")
        draw_21 = ImageDraw.Draw(viz_21_img)
        for zone in la.zones: draw_21.rectangle(zone["bbox"], fill=(200, 200, 200, 100))
        vh.render_separators(draw_21, separators, only_order_changing=False)
        viz_21_img.save(output_dir / "2.1_separator_analysis.png")
        
        # 2.2 Separator Reproduction (High quality PDF-based background + black separators)
        active_seps = [s for s in separators if s.get("order_changing")]
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="2.2_separator_reproduced", 
                            exclude_lines=True, separators=active_seps, draw_text_bbox=False, fill_text_bbox=False, keep_pdf=False)
        
        # 2.3 Token Order Visualization
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="2.3_token_order", exclude_lines=True, keep_pdf=False)
        viz_23_img = Image.open(output_dir / "2.3_token_order.png").convert("RGBA")
        draw_23 = ImageDraw.Draw(viz_23_img)
        vh.render_token_order(draw_23, ordered_tokens)
        viz_23_img.save(output_dir / "2.3_token_order.png")

        # 3.0 Token Glyph Info (Light green shading for tokens)
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="3.0_token_glyph_info", 
                            exclude_lines=True, draw_text_bbox=False, fill_text_bbox=True, keep_pdf=False)
        
        # 3.1 Line & Block Info Visualization (Background text + outlines)
        # For 3.1, we also want the light green shading for tokens
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="3.1_line_block_info", 
                            exclude_lines=True, fill_text_bbox=True, keep_pdf=False)
        viz_31_img = Image.open(output_dir / "3.1_line_block_info.png").convert("RGBA")
        draw_31 = ImageDraw.Draw(viz_31_img)
        # Line & Block outlines (using PIL draw on top of shaded PDF)
        vh.render_line_block_info(draw_31, tokens)
        # Active separators (black)
        vh.render_separators(draw_31, active_seps, only_order_changing=True)
        viz_31_img.save(output_dir / "3.1_line_block_info.png")

        # 3.2 Line & Block Order Visualization
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="3.2_line_block_order", 
                            exclude_lines=True, fill_text_bbox=True, keep_pdf=False)
        viz_32_img = Image.open(output_dir / "3.2_line_block_order.png").convert("RGBA")
        draw_32 = ImageDraw.Draw(viz_32_img)
        vh.render_line_block_info(draw_32, tokens, draw_order=True)
        vh.render_separators(draw_32, active_seps, only_order_changing=True)
        viz_32_img.save(output_dir / "3.2_line_block_order.png")

        # 3.3 Rearranged Structure Visualization
        # Use reproduce_to_pdf with unbroken_block_ids to get green/gray tokens/images automatically
        vh.reproduce_to_pdf(tokens, output_dir, zoom, self.page_width, self.page_height, name="3.3_rearranged_structure", 
                            exclude_lines=True, keep_pdf=False, unbroken_block_ids=unbroken_block_ids)
        viz_33_img = Image.open(output_dir / "3.3_rearranged_structure.png").convert("RGBA")
        draw_33 = ImageDraw.Draw(viz_33_img)
        
        # Calculate unbroken block order based on ordered_tokens
        ordered_unbroken_block_ids = []
        for tk in ordered_tokens:
            bid = tk.get("block_id")
            if bid is not None and bid in unbroken_block_ids:
                if bid not in ordered_unbroken_block_ids:
                    ordered_unbroken_block_ids.append(bid)
        
        # Unbroken block outlines and order numbers
        vh.render_rearranged_structure(draw_33, tokens, ordered_unbroken_block_ids, draw_order=True)
        # Active separators
        vh.render_separators(draw_33, active_seps, only_order_changing=True)
        viz_33_img.save(output_dir / "3.3_rearranged_structure.png")
        
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
