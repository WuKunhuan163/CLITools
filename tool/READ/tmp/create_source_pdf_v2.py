import os
import sys
from fpdf import FPDF
from pathlib import Path

def create_char_table_source():
    font_path = "/Applications/AITerminalTools/resource/fonts/arnhem-blond/arnhem-blond.ttf"
    output_pdf = "/Applications/AITerminalTools/tmp/source.pdf"
    
    if not os.path.exists(font_path):
        print(f"Font not found at {font_path}")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Arnhem-Blond', '', font_path)
    
    # 34pt as discussed
    font_size = 34
    pdf.set_font('Arnhem-Blond', size=font_size)
    
    # Generate all ASCII printable characters (33 to 126)
    # We'll put them in a grid
    chars = "".join([chr(i) for i in range(33, 127)])
    
    cols = 10
    cell_w = 18
    cell_h = 20
    
    x_start = 10
    y_start = 20
    
    for i, char in enumerate(chars):
        row = i // cols
        col = i % cols
        x = x_start + col * cell_w
        y = y_start + row * cell_h
        
        pdf.set_xy(x, y)
        # We use a cell with border=1 to see the logical bbox if needed
        # but for source.pdf we want it clean
        pdf.cell(cell_w, cell_h, char, border=0, align='C')
        
    pdf.output(output_pdf)
    print(f"Structured source PDF created at: {output_pdf}")

if __name__ == "__main__":
    create_char_table_source()

