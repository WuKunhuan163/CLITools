import json
import os

latest_result = "result_20260203_084754_b65c38b7"
result_dir = f"tool/READ/data/pdf/{latest_result}/pages/page_001"
info_path = os.path.join(result_dir, "info.json")

with open(info_path, 'r') as f:
    data = json.load(f)

print(f"--- Digit Token Analysis for {latest_result} ---")
for block in data.get("semantic_blocks", []):
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            text = span["text"]
            if any(c.isdigit() for c in text):
                tags = span.get("tags", {})
                print(f"Token: '{text.strip()}'")
                print(f"  Tags: {tags}")
                if "number" not in tags and "year" not in tags:
                    print(f"  !!! MISSING TAG")


