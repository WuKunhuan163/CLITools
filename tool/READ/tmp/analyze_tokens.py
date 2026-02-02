import fitz
import sys
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
sys.path.append(str(project_root))

from tool.PYTHON.logic.utils import get_python_exec

def analyze():
    pdf_path = project_root / "tool" / "READ" / "logic" / "test" / "001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    doc = fitz.open(str(pdf_path))
    page = doc[6] # Page 7
    words = page.get_text("words") # (x0, y0, x1, y1, word, block_no, line_no, word_no)
    
    # Sort words by Y primarily
    words.sort(key=lambda w: (w[1], w[0]))
    
    for w in words:
        if w[1] > 600: # Focus on the bottom part (References)
            print(f"BBox: {w[0]:.1f}, {w[1]:.1f}, {w[2]:.1f}, {w[3]:.1f} | Text: {w[4]}")

if __name__ == "__main__":
    analyze()
