import numpy as np
from typing import Tuple, List

def is_separator(bbox: Tuple[float, float, float, float], mask: np.ndarray = None) -> bool:
    """
    Determines if a visual component (artifact/image) is a structural separator line.
    """
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    
    # Handle zero-thickness lines (common in some PDF extractions)
    if w < 0 or h < 0:
        return False
        
    # If one dimension is near-zero, it's definitely a line
    if (w > 10 and h <= 1.5) or (h > 10 and w <= 1.5):
        return True
        
    if w == 0 or h == 0:
        return False
        
    # 1. Basic Aspect Ratio Check
    aspect_ratio = max(w / h, h / w)
    if aspect_ratio > 15:
        return True
        
    # 2. Pixel-Aware Check (if mask is provided)
    if mask is not None:
        # ...
        pass
        
    return False

