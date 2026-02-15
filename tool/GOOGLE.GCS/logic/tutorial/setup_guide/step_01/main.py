import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style
from PIL import Image, ImageTk

def build_step(frame, win):
    tk.Label(frame, text="Step 1: Create a Google Cloud Project", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. Go to the Google Cloud Console (https://console.cloud.google.com/).\n\n"
        "2. Click the project dropdown at the top and select 'New Project'.\n\n"
        "3. Give it a name (e.g., 'My-Drive-Manager') and click 'Create'.\n\n"
        "Once done, click 'Next' to continue."
    )
    
    tk.Label(frame, text=content, font=get_label_style(), justify="left", wraplength=600).pack(pady=10, padx=20)
    
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

