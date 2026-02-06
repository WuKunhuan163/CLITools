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
        Predicts logical separators between clusters that change reading order.
        """
        separators = []
        
        # For now, let's look for vertical column separators
        # A vertical separator is a gap that:
        # 1. Has significant height.
        # 2. Has clusters on both its left and right.
        
        # Sort clusters by x
        sorted_clusters = sorted(clusters, key=lambda c: c["bbox"][0])
        
        for i in range(len(sorted_clusters)):
            for j in range(i + 1, len(sorted_clusters)):
                c1 = sorted_clusters[i]
                c2 = sorted_clusters[j]
                
                # Check for horizontal gap
                gap_x0 = c1["bbox"][2]
                gap_x1 = c2["bbox"][0]
                
                if gap_x1 > gap_x0 + 10: # Minimum 10pt gap
                    # Check vertical overlap
                    overlap_y0 = max(c1["bbox"][1], c2["bbox"][1])
                    overlap_y1 = min(c1["bbox"][3], c2["bbox"][3])
                    
                    if overlap_y1 > overlap_y0 + 50: # Minimum 50pt vertical overlap
                        # This is a candidate for a vertical separator
                        separators.append({
                            "type": "separator",
                            "subtype": "vertical",
                            "bbox": [gap_x0, overlap_y0, gap_x1, overlap_y1],
                            "order_changing": True
                        })
        
        return separators

    def visualize_layout(self, clusters: List[Dict[str, Any]], separators: List[Dict[str, Any]], output_path: Path, page_width: int, page_height: int):
        img = Image.new("RGBA", (page_width, page_height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw clusters
        for i, c in enumerate(clusters):
            bbox = c["bbox"]
            draw.rectangle(bbox, outline="blue", width=2)
            draw.text((bbox[0], bbox[1]), f"C{i+1}", fill="blue")
            
        # Draw separators
        for s in separators:
            bbox = s["bbox"]
            color = "red" if s.get("order_changing") else "cyan"
            # Draw as a filled rectangle with alpha
            overlay = Image.new("RGBA", img.size, (0,0,0,0))
            d_overlay = ImageDraw.Draw(overlay)
            d_overlay.rectangle(bbox, fill=(255, 0, 0, 100) if color == "red" else (0, 255, 255, 100))
            img = Image.alpha_composite(img, overlay)
            
        img.save(output_path)

