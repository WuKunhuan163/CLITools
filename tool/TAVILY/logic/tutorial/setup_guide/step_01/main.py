import tkinter as tk
from pathlib import Path
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)

def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

def build_step(frame, win):
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _("tutorial_step1_title", "Step 1: Get a Tavily API Key"), is_title=True)

    content_block = win.add_block(frame)
    content = _(
        "tutorial_step1_content",
        "Tavily provides an AI-optimized search API. "
        "The free tier includes 1,000 searches per month.\n\n"
        "1. Visit [tavily.com](https://tavily.com/) and click 'Get Started' or 'Sign Up'.\n\n"
        "2. Create an account (email or GitHub/Google sign-in).\n\n"
        "3. Once logged in, navigate to 'API Keys' in your dashboard.\n\n"
        "4. Copy your API key (starts with 'tvly-').\n\n"
        "Keep the key ready for the next step."
    )
    win.add_inline_links(content_block, content)
