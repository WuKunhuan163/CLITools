import numpy as np
from typing import Tuple, List

def is_separator(bbox: Tuple[float, float, float, float], mask: np.ndarray = None) -> bool:
    """
    Determines if a visual component (artifact/image) is a structural separator line.
    
    Args:
        bbox: (x0, y0, x1, y1)
        mask: Optional pixel mask of the component.
        
    Returns:
        bool: True if it's a separator line.
    """
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    
    if w <= 0 or h <= 0:
        return False
        
    # 1. Basic Aspect Ratio Check (Horizontal or Vertical)
    # A line is usually very thin in one dimension.
    aspect_ratio = max(w / h, h / w)
    
    # If it's very thin, it's likely a line (e.g., aspect ratio > 15)
    if aspect_ratio > 15:
        return True
        
    # 2. Pixel-Aware Check (if mask is provided)
    if mask is not None:
        # Check if the pixels form a line-like structure
        # (e.g., high density along one axis)
        pass
        
    # 3. Size-based heuristic for smaller lines
    # If it's very short but extremely thin (e.g., 1px thick)
    if (w > 50 and h <= 2) or (h > 50 and w <= 2):
        return True
        
    return False

