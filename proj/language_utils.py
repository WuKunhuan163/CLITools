import json
import os
import unicodedata
from pathlib import Path

def get_display_width(s):
    """Calculate the display width of a string, accounting for full-width characters."""
    width = 0
    for char in s:
        if unicodedata.east_asian_width(char) in ('W', 'F', 'A'):
            width += 2
        else:
            width += 1
    return width

def truncate_to_display_width(s, max_width):
    """Truncate a string to a specific display width."""
    if get_display_width(s) <= max_width:
        return s
    
    current_width = 0
    result = ""
    for char in s:
        char_width = 2 if unicodedata.east_asian_width(char) in ('W', 'F', 'A') else 1
        if current_width + char_width + 3 > max_width:
            break
        result += char
        current_width += char_width
    return result + "..."

def get_translation(tool_proj_dir, key, default_text):
    """
    Looks up a translation for a given key in translations.json.
    Falls back to default_text if not found or if the file is missing.
    """
    # 1. Try to get preferred language from global config
    lang = os.environ.get("TOOL_LANGUAGE")
    
    if not lang:
        try:
            # Find project root
            # language_utils.py is in proj/
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            config_path = project_root / "data" / "global_config.json"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    lang = config.get("language")
        except Exception:
            pass
    
    if not lang:
        lang = "en"
        
    lang = lang.lower()
    
    if lang == "en":
        return default_text
        
    translations_path = Path(tool_proj_dir) / "translations.json"
    if translations_path.exists():
        try:
            with open(translations_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                return translations.get(lang, {}).get(key, default_text)
        except Exception:
            pass
            
    return default_text
