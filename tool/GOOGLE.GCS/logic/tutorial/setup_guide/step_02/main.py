import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    tk.Label(frame, text="Step 2: Enable Google Drive API", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. In the sidebar, go to [APIs & Services > Library](https://console.cloud.google.com/apis/library).\n\n"
        "2. Search for [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com).\n\n"
        "3. Click on it and select 'Enable'.\n\n"
        "This allows your project to communicate with Google Drive."
    )
    
    win.add_inline_links(frame, content)

    # Image support with improved quality
    img_path = Path(__file__).resolve().parent / "asset" / "image" / "guide_1.png"
    if img_path.exists():
        win.setup_image(frame, img_path, max_width=600, upscale=2)
