import os
import sys
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter

def create_arnhem_test_pdf():
    # 1. Setup paths
    font_path = "tool/READ/tmp/arnhem_font_actual/Arnhem Blond/Arnhem Blond.otf"
    output_pdf = "tool/READ/tmp/arnhem_test_title.pdf"
    
    # 2. Register font
    # ReportLab supports OTF if it's CFF-based (which Arnhem Blond usually is)
    try:
        pdfmetrics.registerFont(TTFont('Arnhem-Blond', font_path))
        print(f"Successfully registered font: {font_path}")
    except Exception as e:
        print(f"Error registering font: {e}")
        return

    # 3. Create PDF
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    
    # Title text from NeRF paper
    title_text = "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis"
    
    # Font size 34pt as discussed
    font_size = 34
    c.setFont('Arnhem-Blond', font_size)
    
    # Draw title
    # Center it horizontally
    text_width = c.stringWidth(title_text, 'Arnhem-Blond', font_size)
    x = (width - text_width) / 2
    y = height - 100
    
    # Draw a horizontal line exactly where we expect the overlap to happen
    # BBox Top (usWinAscent 0.873) = 34 * 0.873 = 29.68 pt above baseline
    # Glyph Top (N) ~ 34 * 0.62 = 21.08 pt above baseline
    # Line at 25pt above baseline should be BETWEEN BBox Top and Glyph Top
    line_y = y + 25
    c.setStrokeColorRGB(0.8, 0.8, 0.8) # Light gray line
    c.setLineWidth(0.5)
    c.line(x - 20, line_y, x + text_width + 20, line_y)
    
    # Draw the text
    c.setFillColorRGB(0, 0, 0)
    c.drawString(x, y, title_text)
    
    # Add some labels for clarity (using standard font)
    c.setFont('Helvetica', 8)
    c.setFillColorRGB(1, 0, 0)
    c.drawString(x - 50, line_y, "Line at +25pt")
    c.drawString(x - 50, y, "Baseline")
    
    c.save()
    print(f"Test PDF created at: {output_pdf}")

if __name__ == "__main__":
    create_arnhem_test_pdf()

