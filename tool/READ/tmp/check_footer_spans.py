import json
import os

result_dir = "tool/READ/data/pdf/result_20260203_033702_7383a519/pages/page_001"
info_path = os.path.join(result_dir, "info.json")

with open(info_path, 'r') as f:
    data = json.load(f)

print("--- Detailed Spans for Footer b126 ---")
for block in data.get("semantic_blocks", []):
    if block.get("id") == "b126":
        for i, line in enumerate(block.get("lines", [])):
            print(f"Line {i}:")
            for j, span in enumerate(line.get("spans", [])):
                print(f"  Span {j}: '{span['text']}', Tags: {span.get('tags')}")


