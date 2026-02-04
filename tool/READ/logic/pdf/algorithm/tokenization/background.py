import numpy as np
from PIL import Image
from typing import Tuple, List

def get_background_color(image: Image.Image) -> Tuple[int, int, int]:
    """
    Detect the dominant background color by sampling the four corners 
    and using the median/mode.
    """
    img_data = np.array(image.convert("RGB"))
    h, w, _ = img_data.shape
    
    # Sample corners (10x10 blocks)
    corners = [
        img_data[0:10, 0:10],
        img_data[0:10, w-10:w],
        img_data[h-10:h, 0:10],
        img_data[h-10:h, w-10:w]
    ]
    
    samples = np.concatenate([c.reshape(-1, 3) for c in corners], axis=0)
    # Use median to avoid outliers
    bg_color = np.median(samples, axis=0).astype(int)
    return tuple(bg_color)

def detect_artifacts_from_wiped(original: Image.Image, wiped: Image.Image, bg_color: Tuple[int, int, int]) -> np.ndarray:
    """
    Detect remaining pixels that differ from the background color in the wiped image.
    Used for gradient-aware artifact detection.
    """
    wiped_data = np.array(wiped.convert("RGB")).astype(float)
    bg_data = np.full_like(wiped_data, bg_color)
    
    # Calculate difference
    diff = np.abs(wiped_data - bg_data)
    # Use a threshold for gradient backgrounds
    mask = np.any(diff > 30, axis=2) 
    return mask

def get_artifact_bboxes(mask: np.ndarray, min_area=20) -> List[Tuple[int, int, int, int]]:
    """
    Find bounding boxes for remaining artifact pixels.
    Simple connected components implementation.
    """
    from scipy.ndimage import label
    if not isinstance(mask, np.ndarray) or mask.ndim != 2:
        return []
        
    labeled_array, num_features = label(mask)
    bboxes = []
    if num_features == 0:
        return []
        
    for i in range(1, num_features + 1):
        component_mask = (labeled_array == i)
        rows = np.where(np.any(component_mask, axis=1))[0]
        cols = np.where(np.any(component_mask, axis=0))[0]
        if len(rows) > 0 and len(cols) > 0:
            if len(rows) * len(cols) >= min_area:
                bboxes.append((int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1])))
    return bboxes
