from fontTools.ttLib import TTFont

def check_all_glyphs(font_path):
    font = TTFont(font_path)
    units_per_em = font['head'].unitsPerEm
    glyph_set = font.getGlyphSet()
    
    max_y = -float('inf')
    min_y = float('inf')
    max_glyph = ""
    min_glyph = ""
    
    for glyph_name in glyph_set.keys():
        glyph = glyph_set[glyph_name]
        try:
            # bbox = [xMin, yMin, xMax, yMax]
            if 'CFF ' in font:
                bbox = glyph._glyph.getBoundingBox(font['CFF '].cff.topDictIndex[0].CharStrings)
            else:
                bbox = glyph._glyph.boundingBox
            
            if bbox[3] > max_y:
                max_y = bbox[3]
                max_glyph = glyph_name
            if bbox[1] < min_y:
                min_y = bbox[1]
                min_glyph = glyph_name
        except:
            continue
            
    print(f"Max Y: {max_y} (Ratio: {max_y/units_per_em:.4f}) in glyph '{max_glyph}'")
    print(f"Min Y: {min_y} (Ratio: {min_y/units_per_em:.4f}) in glyph '{min_glyph}'")
    print(f"Font Ascender Ratio (hhea): {font['hhea'].ascent/units_per_em:.4f}")
    print(f"Font Descender Ratio (hhea): {font['hhea'].descent/units_per_em:.4f}")
    if 'OS/2' in font:
        print(f"OS/2 sTypoAscender: {font['OS/2'].sTypoAscender/units_per_em:.4f}")
        print(f"OS/2 sTypoDescender: {font['OS/2'].sTypoDescender/units_per_em:.4f}")
        print(f"OS/2 usWinAscent: {font['OS/2'].usWinAscent/units_per_em:.4f}")
        print(f"OS/2 usWinDescent: {font['OS/2'].usWinDescent/units_per_em:.4f}")

if __name__ == "__main__":
    check_all_glyphs("tool/READ/tmp/arnhem_font_actual/Arnhem Blond/Arnhem Blond.otf")

