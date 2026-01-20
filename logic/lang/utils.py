import json
import os
from pathlib import Path
from logic.config import get_global_config

def get_translation(tool_logic_dir, key, default_text):
    """
    Looks up a translation for a given key in translation.json, 
    or in a translation directory structure.
    """
    # 1. Try to get preferred language from global config or env
    lang = os.environ.get("TOOL_LANGUAGE")
    
    if not lang:
        lang = get_global_config("language")
            
    if not lang:
        lang = "en"
        
    lang = lang.lower()
    
    if lang == "en":
        return default_text
    
    tool_logic_path = Path(tool_logic_dir)
    
    # 2. Try the monolithic translation.json (legacy/standard)
    translation_path = tool_logic_path / "translation.json"
    if translation_path.exists():
        try:
            with open(translation_path, 'r', encoding='utf-8') as f:
                translation = json.load(f)
                result = translation.get(lang, {}).get(key)
                if result:
                    return result
        except Exception:
            pass

    # 3. Try the directory-based translation
    translation_dir = tool_logic_path / "translation"
    if translation_dir.exists():
        # 3a. Try <lang>.json in translation/ directory
        lang_json_path = translation_dir / f"{lang}.json"
        if lang_json_path.exists():
            try:
                with open(lang_json_path, 'r', encoding='utf-8') as f:
                    lang_translation = json.load(f)
                    result = lang_translation.get(key)
                    if result:
                        return result
            except Exception:
                pass
        
        # 3b. Try <lang>/<key>.txt in translation/ directory
        key_file_path = translation_dir / lang / f"{key}.txt"
        if key_file_path.exists():
            try:
                with open(key_file_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
                
    return default_text
