import os
import sys
from fpdf import FPDF
from pathlib import Path

def create_char_table_pdf():
    # 1. Setup paths
    # We use the standardized path in resource/fonts/
    font_path = "/Applications/AITerminalTools/resource/fonts/arnhem-blond/arnhem-blond.ttf"
    output_pdf = "/Applications/AITerminalTools/tmp/source.pdf"
    
    if not os.path.exists(font_path):
        print(f"Font not found at {font_path}")
        return

    # 2. Create PDF
    pdf = FPDF()
    pdf.add_page()
    
    # 3. Add font
    try:
        pdf.add_font('Arnhem-Blond', '', font_path)
        print(f"Successfully added font: {font_path}")
    except Exception as e:
        print(f"Error adding font: {e}")
        return

    # 4. Content
    # All letters, numbers, and some symbols
    char_groups = [
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "abcdefghijklmnopqrstuvwxyz",
        "0123456789",
        "!@#$%^&*()_+-=[]{}|;:,.<>?"
    ]
    
    # Font size 34pt (same as NeRF title)
    font_size = 34
    pdf.set_font('Arnhem-Blond', size=font_size)
    
    y = 30
    for group in char_groups:
        pdf.set_xy(20, y)
        pdf.cell(0, 15, group, border=0, ln=1)
        y += 20
        
    pdf.output(output_pdf)
    print(f"Character table PDF created at: {output_pdf}")

if __name__ == "__main__":
    create_char_table_pdf()

