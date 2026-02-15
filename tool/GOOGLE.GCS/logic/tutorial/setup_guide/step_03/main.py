import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style
from PIL import Image, ImageTk

def build_step(frame, win):
    tk.Label(frame, text="Step 3: Create a Service Account", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. In the sidebar, go to 'APIs & Services' > 'Credentials'.\n\n"
        "2. Click 'Create Credentials' > 'Service Account'.\n\n"
        "3. Enter a name (e.g., 'drive-controller') and click 'Create and Continue'.\n\n"
        "4. (Important) At the 'Grant access' step, you can skip role selection or choose 'Project Editor' for ease of development.\n\n"
        "5. Copy the Service Account Email (e.g., xxx@your-project.iam.gserviceaccount.com)."
    )
    
    tk.Label(frame, text=content, font=get_label_style(), justify="left", wraplength=600).pack(pady=10, padx=20)

    # Image support (multiple images)
    for i in range(1, 3):
        img_path = Path(__file__).resolve().parent / "asset" / "image" / f"guide_{i}.png"
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
                img_label.pack(pady=5)
            except Exception as e:
                print(f"Error loading image {i}: {e}")

