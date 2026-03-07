import tkinter as tk
from pathlib import Path
from interface.gui import get_label_style
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

def build_step(frame, win):
    # Title Block
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _("tutorial_step2_title", "Step 2: Enable Google Drive API"), is_title=True)
    
    # Content Block
    content_block = win.add_block(frame)
    content = _(
        "tutorial_step2_content",
        "1. In the sidebar, go to [APIs & Services > Library](https://console.cloud.google.com/apis/library).\n\n"
        "2. Search for [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com).\n\n"
        "3. Click on it and select 'Enable'.\n\n"
        "This allows your project to communicate with Google Drive."
    )
    win.add_inline_links(content_block, content)

    # Image Block
    img_path = Path(__file__).resolve().parent / "asset" / "image" / "guide_1.png"
    if img_path.exists():
        img_block = win.add_block(frame)
        win.setup_image(img_block, img_path, upscale=2)
