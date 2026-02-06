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

    def predict_separators(self, tokens: List[Dict[str, Any]], page_width: float, page_height: float) -> List[Dict[str, Any]]:
        """
        Predicts logical separators using Distance Transform Ridges with aggressive filtering.
        """
        import numpy as np
        from scipy.ndimage import distance_transform_edt, maximum_filter, label
        
        w, h = int(round(page_width)), int(round(page_height))
        
        # 1. Create content mask
        mask = np.zeros((h, w), dtype=bool)
        for tk in tokens:
            if tk.get("is_absorbed"): continue
            x0, y0, x1, y1 = [int(round(c)) for c in tk["bbox"]]
            mask[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] = True
            
        # 2. Distance Transform of background
        dt = distance_transform_edt(~mask)
        
        # 3. Find ridges (local maxima)
        # Increase threshold to find significant gaps (at least 8px wide at zoom=2)
        # dt > 4 means gap is > 8px wide.
        local_max = (dt == maximum_filter(dt, size=7)) & (dt > 4)
        
        # 4. Connected components of ridges
        labeled_ridges, num_ridges = label(local_max)
        
        separators = []
        for i in range(1, num_ridges + 1):
            m = (labeled_ridges == i)
            coords = np.where(m)
            y_coords, x_coords = coords[0], coords[1]
            
            # Use a much longer minimum length (at least 100px)
            if len(y_coords) < 100: continue 
            
            x0, y0, x1, y1 = np.min(x_coords), np.min(y_coords), np.max(x_coords), np.max(y_coords)
            width = x1 - x0
            height = y1 - y0
            
            # Refine bbox: take the average width/height if it's very thin
            if height > width * 5: # Vertical
                # Adjust x0, x1 to be the center x +/- 2
                avg_x = np.mean(x_coords)
                separators.append({
                    "type": "separator", "subtype": "vertical",
                    "bbox": [float(avg_x - 2), float(y0), float(avg_x + 2), float(y1)],
                    "order_changing": True
                })
            elif width > height * 5: # Horizontal
                avg_y = np.mean(y_coords)
                separators.append({
                    "type": "separator", "subtype": "horizontal",
                    "bbox": [float(x0), float(avg_y - 2), float(x1), float(avg_y + 2)],
                    "order_changing": False
                })
        
        # Merge collinear separators
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
                    
                    # Collinear check
                    is_collinear = False
                    if s1["subtype"] == "vertical":
                        # Check X proximity and Y gap
                        if abs(s1["bbox"][0] - s2["bbox"][0]) < 10:
                            y_gap = max(0, s1["bbox"][1] - s2["bbox"][3], s2["bbox"][1] - s1["bbox"][3])
                            if y_gap < 50: is_collinear = True
                    else: # horizontal
                        # Check Y proximity and X gap
                        if abs(s1["bbox"][1] - s2["bbox"][1]) < 10:
                            x_gap = max(0, s1["bbox"][0] - s2["bbox"][2], s2["bbox"][0] - s1["bbox"][2])
                            if x_gap < 50: is_collinear = True
                    
                    if is_collinear:
                        separators[i]["bbox"] = [
                            min(s1["bbox"][0], s2["bbox"][0]),
                            min(s1["bbox"][1], s2["bbox"][1]),
                            max(s1["bbox"][2], s2["bbox"][2]),
                            max(s1["bbox"][3], s2["bbox"][3])
                        ]
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

