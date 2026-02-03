import os
import sys
from fpdf import FPDF

def create_arnhem_test_pdf_fpdf():
    # 1. Setup paths
    font_path = "tool/READ/tmp/arnhem_font_actual/Arnhem Blond/Arnhem Blond.otf"
    output_pdf = "tool/READ/tmp/arnhem_test_title_fpdf.pdf"
    
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

    # Title text from NeRF paper
    title_text = "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis"
    
    # Font size 34pt
    font_size = 34
    pdf.set_font('Arnhem-Blond', size=font_size)
    
    # Draw title
    # Center it horizontally
    text_width = pdf.get_string_width(title_text)
    page_width = pdf.w
    x = (page_width - text_width) / 2
    y = 50 # Y is from top in fpdf2
    
    # Draw a horizontal line exactly where we expect the overlap to happen
    # In fpdf2, Y is from top. Baseline is at y.
    # BBox Top (usWinAscent 0.873) = 34 * 0.873 = 29.68 pt above baseline
    # 1 pt = 0.352778 mm
    pt_to_mm = 0.352778
    
    line_y_offset_pt = 25
    line_y = y - (line_y_offset_pt * pt_to_mm)
    
    pdf.set_draw_color(200, 200, 200) # Light gray
    pdf.set_line_width(0.2)
    pdf.line(x - 10, line_y, x + text_width + 10, line_y)
    
    # Draw the text
    pdf.set_text_color(0, 0, 0)
    pdf.text(x, y, title_text)
    
    # Add labels
    pdf.set_font('Helvetica', size=8)
    pdf.set_text_color(255, 0, 0)
    pdf.text(x - 20, line_y, "Line at +25pt")
    pdf.text(x - 20, y, "Baseline")
    
    pdf.output(output_pdf)
    print(f"Test PDF created at: {output_pdf}")

if __name__ == "__main__":
    create_arnhem_test_pdf_fpdf()

