from typing import List, Dict, Any, Tuple
import re
import copy

class ImageIdentifier:
    """
    Identifies and merges image artifacts, salient regions, and nearby text.
    Part of Phase A: Tokenization.
    """
    def __init__(self, page_width: float, page_height: float, median_size: float):
        self.page_width = page_width
        self.page_height = page_height
        self.median_size = median_size

    def identify(self, images: List[Dict[str, Any]], tokens: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        1. Merges adjacent/overlapping image items.
        2. Absorbs nearby or contained text tokens into image blocks.
        Returns (merged_image_blocks, remaining_tokens).
        """
        if not images:
            return [], tokens

        # Step 1: Merge image items (artifacts + objects)
        clusters = []
        for it in images:
            bbox = list(it["bbox"])
            merged = False
            for c in clusters:
                dist_x = max(0, max(c["bbox"][0], bbox[0]) - min(c["bbox"][2], bbox[2]))
                dist_y = max(0, max(c["bbox"][1], bbox[1]) - min(c["bbox"][3], bbox[3]))
                if dist_x < 5 and dist_y < 5:
                    c["bbox"] = [min(c["bbox"][0], bbox[0]), min(c["bbox"][1], bbox[1]), 
                                 max(c["bbox"][2], bbox[2]), max(c["bbox"][3], bbox[3])]
                    c["items"].append(it)
                    if it.get("rationale"):
                        c["rationales"].append(it["rationale"])
                    merged = True
                    break
            if not merged:
                clusters.append({"bbox": bbox, "items": [it], "absorbed_text": [], "rationales": [it.get("rationale")] if it.get("rationale") else []})
        
        # Iterative overlap merge
        changed = True
        while changed:
            changed = False
            new_clusters = []
            for c in clusters:
                merged = False
                for nc in new_clusters:
                    dist_x = max(0, max(nc["bbox"][0], c["bbox"][0]) - min(nc["bbox"][2], c["bbox"][2]))
                    dist_y = max(0, max(nc["bbox"][1], c["bbox"][1]) - min(nc["bbox"][3], c["bbox"][3]))
                    if dist_x <= 0 and dist_y <= 0:
                        nc["bbox"] = [min(nc["bbox"][0], c["bbox"][0]), min(nc["bbox"][1], c["bbox"][1]), 
                                      max(nc["bbox"][2], c["bbox"][2]), max(nc["bbox"][3], c["bbox"][3])]
                        nc["items"].extend(c["items"])
                        nc["absorbed_text"].extend(c.get("absorbed_text", []))
                        nc["rationales"].extend(c.get("rationales", []))
                        merged = True
                        changed = True
                        break
                if not merged:
                    new_clusters.append(c)
            clusters = new_clusters

        # Step 2: Smart Text Merging
        remaining_tokens = []
        for i, token in enumerate(tokens):
            t_bbox = token["bbox"]
            min_dist_to_img = float('inf')
            closest_cluster = None
            for c in clusters:
                c_bbox = c["bbox"]
                if (t_bbox[0] >= c_bbox[0] - 2 and t_bbox[2] <= c_bbox[2] + 2 and 
                    t_bbox[1] >= c_bbox[1] - 2 and t_bbox[3] <= c_bbox[3] + 2):
                    min_dist_to_img = 0
                    closest_cluster = c
                    break
                dx = max(0, max(c_bbox[0], t_bbox[0]) - min(c_bbox[2], t_bbox[2]))
                dy = max(0, max(c_bbox[1], t_bbox[1]) - min(c_bbox[3], t_bbox[3]))
                dist = (dx*dx + dy*dy)**0.5
                if dist < min_dist_to_img:
                    min_dist_to_img = dist
                    closest_cluster = c
            
            min_dist_to_text = float('inf')
            for j, other in enumerate(tokens):
                if i == j: continue
                o_bbox = other["bbox"]
                dx = max(0, max(o_bbox[0], t_bbox[0]) - min(o_bbox[2], t_bbox[2]))
                dy = max(0, max(o_bbox[1], t_bbox[1]) - min(o_bbox[3], t_bbox[3]))
                dist = (dx*dx + dy*dy)**0.5
                if dist < min_dist_to_text:
                    min_dist_to_text = dist
            
            is_absorbed = False
            # Relative distance check: text must be significantly closer to image than to other text
            if min_dist_to_img < 3: 
                is_absorbed = True
            elif min_dist_to_img < 10 and min_dist_to_img < min_dist_to_text / 4: # Stricter ratio
                is_absorbed = True
                
            if is_absorbed and closest_cluster:
                c_bbox = closest_cluster["bbox"]
                closest_cluster["bbox"] = [min(c_bbox[0], t_bbox[0]), min(c_bbox[1], t_bbox[1]), 
                                           max(c_bbox[2], t_bbox[2]), max(c_bbox[3], t_bbox[3])]
                closest_cluster["absorbed_text"].append(token["text"])
            else:
                remaining_tokens.append(token)

        merged_image_blocks = []
        for c in clusters:
            block = {
                "type": "unprocessed_image",
                "bbox": c["bbox"],
                "text": "[Merged Image Block]",
                "is_image": True,
                "lines": []
            }
            if c["absorbed_text"]:
                block["merged_texts"] = c["absorbed_text"]
            if c["rationales"]:
                block["rationales"] = list(set(filter(None, c["rationales"])))
            merged_image_blocks.append(block)
            
        return merged_image_blocks, remaining_tokens
