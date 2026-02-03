import json
import os

latest_result = "result_20260203_084754_b65c38b7"
result_dir = f"tool/READ/data/pdf/{latest_result}/pages/page_001"
info_path = os.path.join(result_dir, "info.json")

with open(info_path, 'r') as f:
    data = json.load(f)

print(f"--- Deep Span Tag Analysis for {latest_result} ---")
for block in data.get("semantic_blocks", []):
    if "lines" in block:
        for i, line in enumerate(block["lines"]):
            for j, span in enumerate(line["spans"]):
                if span.get("tags"):
                    print(f"Block {block['id']} Line {i} Span {j} ('{span['text'][:20]}...') has tags: {span['tags']}")
                elif any(c.isdigit() for c in span['text']):
                    print(f"Block {block['id']} Line {i} Span {j} ('{span['text'][:20]}...') MISSING tags on span level.")


