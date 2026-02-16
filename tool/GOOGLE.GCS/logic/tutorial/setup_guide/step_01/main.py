import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    tk.Label(frame, text="Step 1: Create a Google Cloud Project", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. Go to the [Google Cloud Console](https://console.cloud.google.com/).\n\n"
        "2. Click the project dropdown at the top and select 'New Project'.\n\n"
        "3. Give it a name (e.g., 'My-Drive-Manager') and click 'Create'.\n\n"
        "Once done, click 'Next' to continue."
    )
    
    win.add_inline_links(frame, content)
    
    # Image support with improved quality
    img_path = Path(__file__).resolve().parent / "asset" / "image" / "guide_1.png"
    if img_path.exists():
        win.setup_image(frame, img_path, max_width=600, upscale=2)
