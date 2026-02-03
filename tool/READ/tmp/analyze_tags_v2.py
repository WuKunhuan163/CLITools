import json
import os

result_dir = "tool/READ/data/pdf/result_20260203_084724_f5cf1e60/pages/page_001"
info_path = os.path.join(result_dir, "info.json")

with open(info_path, 'r') as f:
    data = json.load(f)

print("--- Analysis of Tags on Page 1 (Improved) ---")
for block in data.get("semantic_blocks", []):
    block_id = block.get("id")
    block_type = block.get("type")
    block_text = block.get("text").replace("\n", "\\n")
    
    print(f"Block {block_id} ({block_type}): {block_text}")
    
    if "tags" in block:
        print(f"  Block Tags: {block['tags']}")
        
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if "tags" in span and span["tags"]:
                print(f"  Token '{span['text']}' Tags: {span['tags']}")
            elif any(c.isdigit() for c in span['text']):
                # Find digits
                digits = "".join([c for c in span['text'] if c.isdigit()])
                print(f"  !!! MISSING TAG: '{span['text']}' contains {digits}")


