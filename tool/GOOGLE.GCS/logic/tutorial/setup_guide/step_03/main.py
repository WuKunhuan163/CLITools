import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    # Title Block
    title_block = win.add_block(frame, pady=(20, 10))
    tk.Label(title_block, text="Step 3: Create a Service Account", font=("Arial", 16, "bold"), bg=title_block.cget("bg")).pack()
    
    # Content Block
    content_block = win.add_block(frame)
    content = (
        "1. In the sidebar, go to 'APIs & Services' > 'Credentials'.\n\n"
        "2. Click 'Create Credentials' > 'Service Account'.\n\n"
        "3. Enter a name (e.g., 'drive-controller') and click 'Create and Continue'.\n\n"
        "4. (Important) At the 'Grant access' step, you can skip role selection or choose 'Project Editor' for ease of development.\n\n"
        "5. Copy the Service Account Email (e.g., xxx@your-project.iam.gserviceaccount.com)."
    )
    tk.Label(content_block, text=content, font=get_label_style(), justify="left", wraplength=600, bg=content_block.cget("bg")).pack(pady=10, padx=20)

    # Image Blocks
    for i in range(1, 3):
        img_path = Path(__file__).resolve().parent / "asset" / "image" / f"guide_{i}.png"
        if img_path.exists():
            img_block = win.add_block(frame)
            win.setup_image(img_block, img_path, max_width=600, upscale=2)
