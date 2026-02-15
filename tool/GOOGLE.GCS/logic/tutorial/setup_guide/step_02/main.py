import tkinter as tk
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    tk.Label(frame, text="Step 2: Enable Google Drive API", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. In the sidebar, go to 'APIs & Services' > 'Library'.\n\n"
        "2. Search for 'Google Drive API'.\n\n"
        "3. Click on it and select 'Enable'.\n\n"
        "This allows your project to communicate with Google Drive."
    )
    
    tk.Label(frame, text=content, font=get_label_style(), justify="left", wraplength=600).pack(pady=10, padx=20)

