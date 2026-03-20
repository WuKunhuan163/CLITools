---
name: computer-vision
description: Computer vision with OpenCV and deep learning. Use when working with computer vision concepts or setting up related projects.
---

# Computer Vision

## Core Techniques

### Image Loading and Processing (OpenCV)
```python
import cv2
import numpy as np

img = cv2.imread("image.jpg")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
edges = cv2.Canny(blurred, 50, 150)
```

### Object Detection (YOLO)
```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
results = model("image.jpg")
for box in results[0].boxes:
    print(f"Class: {box.cls}, Confidence: {box.conf:.2f}")
```

### Image Classification (torchvision)
```python
from torchvision import models, transforms
model = models.resnet50(pretrained=True)
model.eval()
transform = transforms.Compose([
    transforms.Resize(256), transforms.CenterCrop(224),
    transforms.ToTensor(), transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])
```

## Common Tasks
- **Classification**: What is in the image?
- **Detection**: Where are objects? (bounding boxes)
- **Segmentation**: Pixel-level classification
- **OCR**: Text extraction from images

## Data Augmentation
```python
transform = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
])
```
