import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    # Title Block
    title_block = win.add_block(frame, pady=(20, 10))
    tk.Label(title_block, text="Step 5: Share Your Drive Folder", font=("Arial", 16, "bold"), bg=title_block.cget("bg")).pack()
    
    # Content Block
    content_block = win.add_block(frame)
    content = (
        "1. Open [Google Drive](https://drive.google.com/).\n\n"
        "2. Right-click the folder you want to manage and select 'Share'.\n\n"
        "3. Paste the Service Account Email you copied in Step 3.\n\n"
        "4. Set the permission to 'Editor' and click 'Share'.\n\n"
        "Congratulations! You've completed the setup. Click 'Complete' to finish."
    )
    win.add_inline_links(content_block, content)

    # Image Blocks
    for i in range(1, 3):
        img_path = Path(__file__).resolve().parent / "asset" / "image" / f"guide_{i}.png"
        if img_path.exists():
            img_block = win.add_block(frame)
            win.setup_image(img_block, img_path, max_width=600, upscale=2)
