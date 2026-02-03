import fitz
import sys
import json
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from tool.READ.logic.pdf.extractor import extract_single_pdf_page
from tool.READ.logic.pdf.layout import get_median_font_size

def debug_reading_order(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Get median font size
    blocks = page.get_text("dict")["blocks"]
    median_size = get_median_font_size(blocks)
    
    # Create temp output dir
    output_dir = Path("/tmp/gds_read_debug")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"--- Debugging Reading Order for Page {page_num+1} ---")
    content, meta, semantic = extract_single_pdf_page(doc, page_num, output_dir, median_size)
    
    # Filter for body tokens (unprocessed or settled blocks that are part of the main stream)
    print("\n[Predicted Reading Order - First 50 tokens/blocks]")
    for i, item in enumerate(semantic[:50]):
        text = item.get("text", "").replace("\n", " ")[:60]
        type_str = item.get("type", "unknown")
        id_str = item.get("id", "none")
        orig_id = item.get("original_id", "none")
        absorbed_ids = item.get("absorbed_ids", [])
        merged_ids = item.get("merged_ids", [])
        id_info = f" | ORIG_ID: {orig_id}"
        if absorbed_ids: id_info += f" | ABSORBED_IDS: {absorbed_ids[:5]}..."
        if merged_ids: id_info += f" | MERGED_IDS: {merged_ids}"
        
        print(f"{i+1:03d} | ID: {id_str:5s} | TYPE: {type_str:18s} | TEXT: {text}{id_info}")
        
    doc.close()

if __name__ == "__main__":
    pdf_path = "/Applications/AITerminalTools/tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    debug_reading_order(pdf_path, 0)
