import tkinter as tk
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    tk.Label(frame, text="Step 5: Share Your Drive Folder", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. Open Google Drive (https://drive.google.com/).\n\n"
        "2. Right-click the folder you want to manage and select 'Share'.\n\n"
        "3. Paste the Service Account Email you copied in Step 3.\n\n"
        "4. Set the permission to 'Editor' and click 'Share'.\n\n"
        "Congratulations! You've completed the setup. Click 'Complete' to finish."
    )
    
    tk.Label(frame, text=content, font=get_label_style(), justify="left", wraplength=600).pack(pady=10, padx=20)

