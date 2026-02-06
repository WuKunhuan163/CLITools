import numpy as np
from typing import List, Dict, Any, Tuple
from pathlib import Path
from PIL import Image, ImageDraw

class LayoutAnalyzer:
    def __init__(self, median_size: float):
        self.median_size = median_size

    def cluster_tokens(self, tokens: List[Dict[str, Any]], h_threshold: float = 30, v_threshold: float = 10) -> List[Dict[str, Any]]:
        """
        Groups tokens into clusters based on proximity.
        """
        if not tokens: return []
        
        # Prepare clusters (initially each token is a cluster)
        clusters = []
        for tk in tokens:
            if tk.get("is_absorbed"): continue
            clusters.append({
                "bbox": list(tk["bbox"]),
                "token_ids": [tk["id"]],
                "type": tk["type"]
            })
            
        merged = True
        while merged:
            merged = False
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    if self._is_nearby(clusters[i]["bbox"], clusters[j]["bbox"], h_threshold, v_threshold):
                        # Merge j into i
                        clusters[i]["bbox"] = [
                            min(clusters[i]["bbox"][0], clusters[j]["bbox"][0]),
                            min(clusters[i]["bbox"][1], clusters[j]["bbox"][1]),
                            max(clusters[i]["bbox"][2], clusters[j]["bbox"][2]),
                            max(clusters[i]["bbox"][3], clusters[j]["bbox"][3])
                        ]
                        clusters[i]["token_ids"].extend(clusters[j]["token_ids"])
                        clusters.pop(j)
                        merged = True
                        break
                if merged: break
        
        return clusters

    def _is_nearby(self, bbox1: List[float], bbox2: List[float], h_thresh: float, v_thresh: float) -> bool:
        # Check horizontal proximity
        h_overlap = min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0])
        v_overlap = min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1])
        
        # If they overlap or are very close
        if h_overlap > -h_thresh and v_overlap > -v_thresh:
            # Additional check: are they actually close in at least one dimension?
            # (If they are far in both, they are not nearby)
            
            # Horizontal distance
            dx = max(0, bbox1[0] - bbox2[2], bbox2[0] - bbox1[2])
            # Vertical distance
            dy = max(0, bbox1[1] - bbox2[3], bbox2[1] - bbox1[3])
            
            return dx < h_thresh and dy < v_thresh
            
        return False

    def predict_separators(self, clusters: List[Dict[str, Any]], page_width: float, page_height: float) -> List[Dict[str, Any]]:
        """
        Predicts logical separators between clusters.
        """
        separators = []
        
        # 1. Vertical Separators (Potential Column Splits)
        sorted_x = sorted(clusters, key=lambda c: c["bbox"][0])
        for i in range(len(sorted_x)):
            for j in range(i + 1, len(sorted_x)):
                c1, c2 = sorted_x[i], sorted_x[j]
                
                # Gap in X
                gap_x0 = c1["bbox"][2]
                gap_x1 = c2["bbox"][0]
                
                if gap_x1 > gap_x0 + 10:
                    # Vertical overlap
                    v_overlap_y0 = max(c1["bbox"][1], c2["bbox"][1])
                    v_overlap_y1 = min(c1["bbox"][3], c2["bbox"][3])
                    
                    if v_overlap_y1 > v_overlap_y0 + 100: # Significant vertical overlap
                        separators.append({
                            "type": "separator", "subtype": "vertical",
                            "bbox": [gap_x0, v_overlap_y0, gap_x1, v_overlap_y1],
                            "order_changing": True
                        })
                        
        # 2. Horizontal Separators (Content Divisions)
        sorted_y = sorted(clusters, key=lambda c: c["bbox"][1])
        for i in range(len(sorted_y)):
            for j in range(i + 1, len(sorted_y)):
                c1, c2 = sorted_y[i], sorted_y[j]
                
                # Gap in Y
                gap_y0 = c1["bbox"][3]
                gap_y1 = c2["bbox"][1]
                
                if gap_y1 > gap_y0 + 15:
                    # Horizontal overlap
                    h_overlap_x0 = max(c1["bbox"][0], c2["bbox"][0])
                    h_overlap_x1 = min(c1["bbox"][2], c2["bbox"][2])
                    
                    if h_overlap_x1 > h_overlap_x0 + 100: # Significant horizontal overlap
                        separators.append({
                            "type": "separator", "subtype": "horizontal",
                            "bbox": [h_overlap_x0, gap_y0, h_overlap_x1, gap_y1],
                            "order_changing": False
                        })
        
        # 3. Refine: Merge overlapping/nearby separators of the same type
        separators = self._merge_separators(separators)
        
        return separators

    def _merge_separators(self, separators: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not separators: return []
        
        merged = True
        while merged:
            merged = False
            for i in range(len(separators)):
                for j in range(i + 1, len(separators)):
                    s1, s2 = separators[i], separators[j]
                    if s1["subtype"] != s2["subtype"]: continue
                    
                    # If they overlap or are very close, merge them
                    if self._is_nearby(s1["bbox"], s2["bbox"], 10, 10):
                        separators[i]["bbox"] = [
                            min(s1["bbox"][0], s2["bbox"][0]),
                            min(s1["bbox"][1], s2["bbox"][1]),
                            max(s1["bbox"][2], s2["bbox"][2]),
                            max(s1["bbox"][3], s2["bbox"][3])
                        ]
                        # If either is order-changing, the merged one is too (aggressive)
                        separators[i]["order_changing"] = s1["order_changing"] or s2["order_changing"]
                        separators.pop(j)
                        merged = True
                        break
                if merged: break
        return separators

    def visualize_layout(self, clusters: List[Dict[str, Any]], separators: List[Dict[str, Any]], output_path: Path, page_width: int, page_height: int, background_img: Image.Image = None):
        if background_img:
            img = background_img.convert("RGBA").copy()
            # Ensure background matches expected size
            if img.size != (page_width, page_height):
                img = img.resize((page_width, page_height), Image.LANCZOS)
        else:
            img = Image.new("RGBA", (page_width, page_height), (255, 255, 255, 255))
            
        draw = ImageDraw.Draw(img)
        
        # 1. Draw clusters (subtle outline)
        for i, c in enumerate(clusters):
            bbox = c["bbox"]
            draw.rectangle(bbox, outline=(0, 0, 255, 100), width=1)
            # draw.text((bbox[0], bbox[1]), f"C{i+1}", fill=(0, 0, 255, 150))
            
        # 2. Draw separators
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d_overlay = ImageDraw.Draw(overlay)
        
        for s in separators:
            bbox = s["bbox"]
            is_order_changing = s.get("order_changing", False)
            color = (255, 0, 0, 180) if is_order_changing else (0, 0, 255, 180)
            
            # Draw as a slightly thicker line/box
            d_overlay.rectangle(bbox, fill=color)
            
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img) # Refresh draw for final elements
        
        # 3. Draw Legend at the bottom
        legend_h = 40
        legend_y = page_height - legend_h
        draw.rectangle([0, legend_y, page_width, page_height], fill=(240, 240, 240, 255))
        
        # Red Legend
        draw.rectangle([20, legend_y + 10, 50, legend_y + 30], fill=(255, 0, 0, 255))
        draw.text((60, legend_y + 12), "Order-Changing Separator", fill="black")
        
        # Blue Legend
        draw.rectangle([250, legend_y + 10, 280, legend_y + 30], fill=(0, 0, 255, 255))
        draw.text((290, legend_y + 12), "Content-Dividing Separator (Order-Preserving)", fill="black")
        
        img.save(output_path)

