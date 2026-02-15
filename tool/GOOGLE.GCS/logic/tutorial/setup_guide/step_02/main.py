import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style
from PIL import Image, ImageTk

def build_step(frame, win):
    tk.Label(frame, text="Step 2: Enable Google Drive API", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. In the sidebar, go to [APIs & Services > Library](https://console.cloud.google.com/apis/library).\n\n"
        "2. Search for [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com).\n\n"
        "3. Click on it and select 'Enable'.\n\n"
        "This allows your project to communicate with Google Drive."
    )
    
    win.add_inline_links(frame, content)

    # Image support
    img_path = Path(__file__).resolve().parent / "asset" / "image" / "guide_1.png"
    if img_path.exists():
        try:
            img = Image.open(img_path)
            # Resize if too large
            if img.width > 500:
                ratio = 500 / img.width
                img = img.resize((500, int(img.height * ratio)), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(frame, image=photo)
            img_label.image = photo # Keep a reference
            img_label.pack(pady=10)
        except Exception as e:
            print(f"Error loading image: {e}")

