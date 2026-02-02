import fitz
import sys
from pathlib import Path

def analyze_tokens(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    
    # Get words: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
    words = page.get_text("words")
    
    print(f"Total words found: {len(words)}")
    
    # Find "References"
    ref_idx = -1
    for i, w in enumerate(words):
        if "Reference" in w[4]:
            print(f"Found '{w[4]}' at index {i}, bbox=({w[0]:.1f}, {w[1]:.1f}, {w[2]:.1f}, {w[3]:.1f})")
            ref_idx = i
            break
            
    if ref_idx != -1:
        print("\n--- Next 50 words after 'References' ---")
        for i in range(ref_idx, min(ref_idx + 50, len(words))):
            w = words[i]
            print(f"[{i:03d}] bbox=({w[0]:.1f}, {w[1]:.1f}, {w[2]:.1f}, {w[3]:.1f}) text='{w[4]}' block={w[5]} line={w[6]}")

if __name__ == "__main__":
    pdf = "tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    analyze_tokens(pdf, 7)
