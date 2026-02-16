import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    # Title Block
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, "Step 1: Create a Google Cloud Project", is_title=True)
    
    # Content Block
    content_block = win.add_block(frame)
    content = (
        "1. Go to the [Google Cloud Console](https://console.cloud.google.com/).\n\n"
        "2. Click the project dropdown at the top and select 'New Project'.\n\n"
        "3. Give it a name (e.g., 'My-Drive-Manager') and click 'Create'.\n\n"
        "Once done, click 'Next' to continue."
    )
    win.add_inline_links(content_block, content)
    
    # Image Block
    img_path = Path(__file__).resolve().parent / "asset" / "image" / "guide_1.png"
    if img_path.exists():
        img_block = win.add_block(frame)
        win.setup_image(img_block, img_path, max_width=600, upscale=2)
