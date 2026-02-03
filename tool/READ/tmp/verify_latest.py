import json
import os

latest_result = "result_20260203_084956_56acc436"
result_dir = f"tool/READ/data/pdf/{latest_result}/pages/page_001"
info_path = os.path.join(result_dir, "info.json")

with open(info_path, 'r') as f:
    data = json.load(f)

print(f"--- Analysis of {latest_result} ---")
for block in data.get("semantic_blocks", []):
    tags = block.get("tags")
    if tags:
        print(f"Block {block['id']} ({block['type']}):")
        safe_text = block['text'].replace('\n', ' ')
        print(f"  Text: {safe_text[:100]}...")
        print(f"  Tags: {tags}")
        
        # Also check spans to be sure
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("tags"):
                    print(f"    Span '{span['text']}': {span['tags']}")
