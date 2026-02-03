import json
import os

result_dir = "tool/READ/data/pdf/result_20260203_033702_7383a519/pages/page_001"
info_path = os.path.join(result_dir, "info.json")

if not os.path.exists(info_path):
    print(f"Error: {info_path} does not exist")
    exit(1)

with open(info_path, 'r') as f:
    data = json.load(f)

print(f"Found {len(data.get('semantic_blocks', []))} blocks.")
for block in data.get("semantic_blocks", []):
    if block.get("id") == "b126":
        print(f"Block {block.get('id')} found!")
        print(f"Text: {block.get('text')}")
        lines = block.get("lines", [])
        print(f"Lines count: {len(lines)}")
        for i, line in enumerate(lines):
            spans = line.get("spans", [])
            print(f"  Line {i} spans: {len(spans)}")
            for j, span in enumerate(spans):
                print(f"    Span {j}: '{span['text']}', Tags: {span.get('tags')}")


