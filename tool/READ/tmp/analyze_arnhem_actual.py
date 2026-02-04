import os
from fontTools.ttLib import TTFont
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def get_glyph_metrics(font_path, char):
    """
    Extract detailed metrics and glyph bbox for a character.
    """
    font = TTFont(font_path)
    
    # Get units per em
    units_per_em = font['head'].unitsPerEm
    
    # Get hhea metrics
    ascender = font['hhea'].ascent
    descender = font['hhea'].descent
    line_gap = font['hhea'].lineGap
    
    # Get glyph set
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    glyph_name = cmap.get(ord(char))
    
    if not glyph_name:
        return None
        
    glyph = glyph_set[glyph_name]
    
    # BBox in font units
    # glyph.lsb, glyph.width are also available
    # For OTF (CFF), we might need to look at the 'hmtx' and glyph data
    
    # Get actual bbox from the 'hmtx' and glyph data
    # For CFF fonts, the bbox is often stored in the glyph data
    try:
        # This works for both TTF and OTF (usually)
        bbox = glyph._glyph.getBoundingBox(font['CFF '].cff.topDictIndex[0].CharStrings) if 'CFF ' in font else glyph._glyph.boundingBox
    except AttributeError:
        # Fallback for different fontTypes
        bbox = (0, 0, 0, 0)
        if hasattr(glyph, 'draw'):
            from fontTools.pens.boundsPen import BoundsPen
            pen = BoundsPen(glyph_set)
            glyph.draw(pen)
            bbox = pen.bounds if pen.bounds else (0, 0, 0, 0)

    # Convert to ratios (standardized)
    ascender_ratio = ascender / units_per_em
    descender_ratio = descender / units_per_em
    
    # Glyph bbox ratios relative to baseline
    # Font units: y is up from baseline
    gx0, gy0, gx1, gy1 = bbox
    glyph_bbox_ratios = (gx0/units_per_em, gy0/units_per_em, gx1/units_per_em, gy1/units_per_em)
    
    return {
        'units_per_em': units_per_em,
        'ascender': ascender_ratio,
        'descender': descender_ratio,
        'line_gap': line_gap / units_per_em,
        'glyph_bbox_ratios': glyph_bbox_ratios, # (x0, y0, x1, y1) relative to baseline
        'total_height': (ascender - descender) / units_per_em
    }

def analyze_arnhem_otf():
    font_path = "tool/READ/tmp/arnhem_font_actual/Arnhem Blond/Arnhem Blond.otf"
    char_to_test = "N"
    
    metrics = get_glyph_metrics(font_path, char_to_test)
    if not metrics:
        print(f"Could not find metrics for '{char_to_test}'")
        return

    print(f"--- Arnhem Blond Analysis ({char_to_test}) ---")
    print(f"Ascender Ratio: {metrics['ascender']:.4f}")
    print(f"Descender Ratio: {metrics['descender']:.4f}")
    print(f"Line Gap Ratio: {metrics['line_gap']:.4f}")
    
    x0, y0, x1, y1 = metrics['glyph_bbox_ratios']
    print(f"Glyph BBox Ratios (rel to baseline): x0={x0:.4f}, y0={y0:.4f}, x1={x1:.4f}, y1={y1:.4f}")
    
    # Simulation at size 34.0 pt, Zoom 2.0
    size_pt = 34.0
    zoom = 2.0
    px_per_unit = (size_pt * zoom) / 1.0 # In our READ tool, 1.0 unit = size_pt * zoom pixels
    
    # Wait, in PDF, font size S means 1 unit = S points. 
    # At zoom Z, 1 point = Z pixels. So 1 unit = S * Z pixels.
    px_per_unit = size_pt * zoom
    
    glyph_top_px = -y1 * px_per_unit # y is up in font, so top is -y1 from baseline in image
    glyph_bottom_px = -y0 * px_per_unit
    
    theoretical_top_px = -metrics['ascender'] * px_per_unit
    theoretical_bottom_px = -metrics['descender'] * px_per_unit
    
    print(f"\nSimulation at {size_pt}pt (Zoom {zoom}):")
    print(f"BBox Top (rel to baseline): {theoretical_top_px:.2f} px")
    print(f"BBox Bottom (rel to baseline): {theoretical_bottom_px:.2f} px")
    print(f"Glyph Top (rel to baseline): {glyph_top_px:.2f} px")
    print(f"Glyph Bottom (rel to baseline): {glyph_bottom_px:.2f} px")
    
    print(f"Buffer at Top: {glyph_top_px - theoretical_top_px:.2f} px")
    print(f"Buffer at Bottom: {theoretical_bottom_px - glyph_bottom_px:.2f} px")

    # Render actual image to verify
    img_h = 200
    img_w = 200
    img = Image.new('RGB', (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    baseline = 120
    
    try:
        pil_font = ImageFont.truetype(font_path, int(size_pt * zoom))
        draw.text((50, baseline), char_to_test, font=pil_font, fill=(0,0,0), anchor="ls")
        
        # Draw theoretical bbox
        draw.rectangle([50, baseline + theoretical_top_px, 150, baseline + theoretical_bottom_px], outline="red", width=1)
        # Draw glyph bbox
        draw.rectangle([50 + x0*px_per_unit, baseline + glyph_top_px, 50 + x1*px_per_unit, baseline + glyph_bottom_px], outline="blue", width=1)
        
        save_path = "tool/READ/tmp/arnhem_actual_render.png"
        img.save(save_path)
        print(f"Rendered comparison saved to {save_path}")
    except Exception as e:
        print(f"Error rendering: {e}")

if __name__ == "__main__":
    analyze_arnhem_otf()

