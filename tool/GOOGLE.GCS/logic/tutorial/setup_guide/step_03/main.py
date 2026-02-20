import tkinter as tk
from pathlib import Path
from logic.gui.tkinter.style import get_label_style

def build_step(frame, win):
    # Title Block
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, "Step 3: Create a Service Account", is_title=True)
    
    # Content Block
    content_block = win.add_block(frame)
    content = (
        "1. In the sidebar, go to 'APIs & Services' > 'Credentials'.\n\n"
        "2. Click 'Create Credentials' > 'Service Account'.\n\n"
        "3. Enter a name (e.g., 'drive-controller') and click 'Create and Continue'.\n\n"
        "4. (Important) At the 'Grant access' step, you can skip role selection or choose 'Project Editor' for ease of development.\n\n"
        "5. Copy the Service Account Email below for verification in the next steps."
    )
    win.setup_label(content_block, content)

    # Action Block
    action_block = win.add_block(frame)
    block_bg = "#f9f9f9" if getattr(win, "debug_blocks", False) else action_block.cget("bg")
    
    tk.Label(action_block, text="Service Account Email:", font=get_label_style(), bg=block_bg).pack(pady=(10, 0))
    
    email_var = tk.StringVar(value=win.tutorial_data.get("service_email", ""))
    email_entry = tk.Entry(action_block, textvariable=email_var, width=50, font=get_label_style())
    email_entry.pack(pady=5)
    
    def on_email_change(*args):
        email = email_var.get().strip()
        if "@" in email and "." in email:
            win.tutorial_data["service_email"] = email
            win.set_step_validated(True)
        else:
            win.set_step_validated(False)
            
    email_var.trace_add("write", on_email_change)
    
    # Initial validation check
    on_email_change()

    # Image Blocks
    for i in range(1, 3):
        img_path = Path(__file__).resolve().parent / "asset" / "image" / f"guide_{i}.png"
        if img_path.exists():
            img_block = win.add_block(frame)
            win.setup_image(img_block, img_path, upscale=2)
