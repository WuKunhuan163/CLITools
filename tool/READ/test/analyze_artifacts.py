import sys
from PIL import Image
import numpy as np
from pathlib import Path

def analyze_artifact(path):
    img = Image.open(path).convert("L")
    data = np.array(img)
    print(f"Artifact: {path.name}")
    print(f"  Shape: {data.shape}")
    print(f"  Min Intensity: {np.min(data)}")
    print(f"  Max Intensity: {np.max(data)}")
    print(f"  Mean Intensity: {np.mean(data):.2f}")
    print(f"  Pixel Data (top-left 5x5 if possible):")
    print(data[:5, :5])

if __name__ == "__main__":
    base_dir = Path("/Applications/AITerminalTools/tool/READ/data/pdf/result_20260203_150648_440e1636/pages/page_001/images/tokenized/")
    for i in range(21, 24):
        p = base_dir / f"art_00{i}.png"
        if p.exists():
            analyze_artifact(p)

