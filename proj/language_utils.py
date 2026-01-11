import json
import os
from pathlib import Path

def get_translation(tool_proj_dir, key, default_text):
    """
    Looks up a translation for a given key in translations.json, 
    or in a translations directory structure.
    """
    # 1. Try to get preferred language from global config or env
    lang = os.environ.get("TOOL_LANGUAGE")
    
    if not lang:
        try:
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
    
    tool_proj_path = Path(tool_proj_dir)
    
    # 2. Try the monolithic translations.json (legacy/standard)
    translations_path = tool_proj_path / "translations.json"
    if translations_path.exists():
        try:
            with open(translations_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                result = translations.get(lang, {}).get(key)
                if result:
                    return result
        except Exception:
            pass

    # 3. Try the directory-based translations
    translations_dir = tool_proj_path / "translations"
    if translations_dir.exists():
        # 3a. Try <lang>.json in translations/ directory
        lang_json_path = translations_dir / f"{lang}.json"
        if lang_json_path.exists():
            try:
                with open(lang_json_path, 'r', encoding='utf-8') as f:
                    lang_translations = json.load(f)
                    result = lang_translations.get(key)
                    if result:
                        return result
            except Exception:
                pass
        
        # 3b. Try <lang>/<key>.txt in translations/ directory
        key_file_path = translations_dir / lang / f"{key}.txt"
        if key_file_path.exists():
            try:
                with open(key_file_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
                
    return default_text
