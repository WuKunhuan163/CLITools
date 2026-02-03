import fitz

def create_simulated_pdf(output_path):
    doc = fitz.open()
    page = doc.new_page()
    
    # 1. Draw a line at Y = 54.6
    # Drawing a line from X=42 to X=550 at Y=54.6
    shape = page.new_shape()
    shape.draw_line(fitz.Point(42, 54.6), fitz.Point(550, 54.6))
    shape.finish(color=(0, 0, 0), width=0.4)
    shape.commit()
    
    # 2. Insert text 'NeRF' near it
    # We want the glyph top to be around 54.5
    # The origin (baseline) for 34pt font with ascender ~0.87 is roughly:
    # 54.5 + (34 * 0.87) = 54.5 + 29.58 = 84.08
    # Let's try inserting at (41.75, 80.96) as seen in the real PDF
    font = fitz.Font("helv") # Use a standard font
    page.insert_text((41.75, 80.96), "NeRF: Representing Scenes", fontname="helv", fontsize=34)
    
    doc.save(output_path)
    doc.close()
    print(f"Simulated PDF created at {output_path}")

if __name__ == "__main__":
    create_simulated_pdf("tool/READ/test/simulated_nerf.pdf")


