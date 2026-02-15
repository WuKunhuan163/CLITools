import tkinter as tk
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    tk.Label(frame, text="Step 4: Generate JSON Key", font=("Arial", 16, "bold")).pack(pady=(20, 10))
    
    content = (
        "1. Click on the newly created Service Account from the list.\n\n"
        "2. Go to the 'Keys' tab.\n\n"
        "3. Click 'Add Key' > 'Create New Key'.\n\n"
        "4. Select 'JSON' and click 'Create'.\n\n"
        "5. A JSON file will be downloaded. Save it to 'data/google/console_key.json' in this project root."
    )
    
    tk.Label(frame, text=content, font=get_label_style(), justify="left", wraplength=600).pack(pady=10, padx=20)

