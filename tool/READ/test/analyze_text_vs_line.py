import sys
from PIL import Image
import numpy as np
from pathlib import Path

def analyze_text_vs_line(image_path, text_bbox, line_y):
    img = Image.open(image_path).convert("L")
    zoom = 2.0
    
    # Text bbox in points, convert to pixels
    tx0, ty0, tx1, ty1 = [int(c * zoom) for c in text_bbox]
    
    print(f"Analyzing Text BBox: {tx0},{ty0} to {tx1},{ty1}")
    text_region = img.crop((tx0, ty0, tx1, ty1))
    text_data = np.array(text_region)
    
    # Histogram of intensities in text bbox
    counts, bins = np.histogram(text_data, bins=10, range=(0, 255))
    print("Intensity histogram in text bbox:")
    for i in range(len(counts)):
        print(f"  {bins[i]:.0f}-{bins[i+1]:.0f}: {counts[i]}")
    
    print(f"Min intensity in text bbox: {np.min(text_data)}")
    
    # Analyze the line nearby
    line_y_px = int(line_y * zoom)
    line_strip = img.crop((tx0, line_y_px - 2, tx1, line_y_px + 2))
    line_data = np.array(line_strip)
    print(f"Min intensity in line nearby: {np.min(line_data)}")

if __name__ == "__main__":
    # Path from the last successful run
    result_path = "/Applications/AITerminalTools/tool/READ/data/pdf/result_20260203_150648_440e1636/pages/page_001/source.png"
    # Title "NeRF:" bbox from previous info.json: [41.75, 51.28, 132.46, 90.21]
    # Line is around y=53
    analyze_text_vs_line(result_path, [41.75, 51.28, 132.46, 90.21], 53)

