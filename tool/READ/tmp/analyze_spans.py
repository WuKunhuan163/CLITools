import pymupdf as fitz
import json

doc = fitz.open("tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf")
page = doc[0]
page_dict = page.get_text("dict")

spans = []
for b in page_dict["blocks"]:
    if b.get("type") != 0: continue
    for line in b["lines"]:
        for span in line["spans"]:
            spans.append({
                "text": span["text"],
                "bbox": [round(x, 2) for x in span["bbox"]],
                "origin": [round(x, 2) for x in span["origin"]],
                "size": round(span["size"], 2),
                "font": span["font"]
            })

# Print first 20 spans
for i, s in enumerate(spans[:50]):
    print(f"{i:3d} | {s['text']:30s} | {s['bbox']} | {s['origin']}")

doc.close()




