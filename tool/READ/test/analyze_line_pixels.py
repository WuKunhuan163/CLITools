import sys
from PIL import Image, ImageStat
from pathlib import Path
import numpy as np

def analyze_line_pixels(image_path, y_range=(40, 60)):
    img = Image.open(image_path).convert("L")
    w, h = img.size
    zoom = 2.0 # Assuming zoom 2.0 as in extractor
    
    # Analyze a horizontal strip
    y_start = int(y_range[0] * zoom)
    y_end = int(y_range[1] * zoom)
    
    print(f"Analyzing pixel intensity in Y range {y_start}-{y_end} (zoom {zoom})")
    
    # Get the strip
    strip = img.crop((0, y_start, w, y_end))
    data = np.array(strip)
    
    # For each column, find the minimum intensity (darkest pixel)
    min_intensities = np.min(data, axis=0)
    
    print("Column-wise minimum intensities (first 100 columns):")
    print(min_intensities[:100])
    
    # Find columns where there is something dark (intensity < 240)
    dark_cols = np.where(min_intensities <= 240)[0]
    print(f"Found {len(dark_cols)} columns with pixels <= 240.")
    
    # Group into contiguous segments
    if len(dark_cols) > 0:
        segments = []
        start = dark_cols[0]
        for i in range(1, len(dark_cols)):
            if dark_cols[i] > dark_cols[i-1] + 1:
                segments.append((start, dark_cols[i-1]))
                start = dark_cols[i]
        segments.append((start, dark_cols[-1]))
        
        print(f"Detected {len(segments)} segments of dark pixels horizontally:")
        for s in segments:
            avg_intensity = np.mean(min_intensities[s[0]:s[1]+1])
            print(f"  Segment: x={s[0]}-{s[1]} (width={s[1]-s[0]+1}), avg_min_intensity={avg_intensity:.2f}")

if __name__ == "__main__":
    # Path from the last successful run mentioned in terminal
    result_path = "/Applications/AITerminalTools/tool/READ/data/pdf/result_20260203_145819_443be07d/pages/page_001/source.png"
    if Path(result_path).exists():
        analyze_line_pixels(result_path)
    else:
        print(f"File not found: {result_path}")

