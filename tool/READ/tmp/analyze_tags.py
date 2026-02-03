import json
import os

result_dir = "tool/READ/data/pdf/result_20260203_033702_7383a519/pages/page_001"
info_path = os.path.join(result_dir, "info.json")

with open(info_path, 'r') as f:
    data = json.load(f)

print("--- Analysis of Tags on Page 1 ---")
for block in data.get("semantic_blocks", []):
    block_id = block.get("id")
    block_type = block.get("type")
    block_text = block.get("text")
    
    print(f"Block {block_id} ({block_type}): {block_text}")
    
    # Check top-level tags
    if "tags" in block:
        print(f"  Top-level Tags: {block['tags']}")
        
    # Check span-level tags
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if "tags" in span and span["tags"]:
                print(f"  Token '{span['text']}' Tags: {span['tags']}")
            elif any(c.isdigit() for c in span['text']):
                 print(f"  MISSING TAG? Token '{span['text']}' contains digits but has no tags.")


