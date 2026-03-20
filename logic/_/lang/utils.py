import json
import os
from pathlib import Path

_ROOT_LOGIC_CACHE = {}

def _find_root_logic(tool_logic_path: Path) -> Path:
    """Walk up from a tool's logic dir to find the project root logic/."""
    key = str(tool_logic_path)
    if key in _ROOT_LOGIC_CACHE:
        return _ROOT_LOGIC_CACHE[key]
    curr = tool_logic_path.resolve()
    while curr != curr.parent:
        if ((curr / "bin" / "TOOL").exists() and
                (curr / "logic" / "translation").is_dir()):
            result = curr / "logic"
            _ROOT_LOGIC_CACHE[key] = result
            return result
        curr = curr.parent
    _ROOT_LOGIC_CACHE[key] = None
    return None


def get_translation(tool_logic_dir, key, default_text, lang_code=None, **kwargs):
    """
    Looks up a translation for a given key in translation.json, 
    or in a translation directory structure.
    
    Supports {{recursive_key}} for nested translations.
    Supports {literal_key} for standard formatting.
    """
    import re
    
    # 1. Try to get preferred language from global config or env
    lang = lang_code or os.environ.get("TOOL_LANGUAGE")
    
    if not lang:
        from logic._.config import get_global_config
        lang = get_global_config("language")
            
    if not lang:
        lang = "en"
        
    lang = lang.lower()
    
    translated_text = default_text
    
    if lang != "en":
        tool_logic_path = Path(tool_logic_dir)
        found = False
        
        # 2. Try the directory-based translation (preferred format)
        translation_dir = tool_logic_path / "translation"
        if translation_dir.exists():
            lang_json_path = translation_dir / f"{lang}.json"
            if lang_json_path.exists():
                try:
                    with open(lang_json_path, 'r', encoding='utf-8') as f:
                        lang_translation = json.load(f)
                        result = lang_translation.get(key)
                        if result:
                            translated_text = result
                            found = True
                except Exception:
                    pass

            if not found:
                key_file_path = translation_dir / lang / f"{key}.txt"
                if key_file_path.exists():
                    try:
                        with open(key_file_path, 'r', encoding='utf-8') as f:
                            translated_text = f.read().strip()
                            found = True
                    except Exception:
                        pass

        # 3. Fallback: monolithic translation.json (deprecated)
        if not found:
            translation_path = tool_logic_path / "translation.json"
            if translation_path.exists():
                try:
                    with open(translation_path, 'r', encoding='utf-8') as f:
                        translation = json.load(f)
                        result = translation.get(lang, {}).get(key)
                        if result:
                            translated_text = result
                            found = True
                except Exception:
                    pass

        # 4. Fallback: root logic/translation/ (for tool descriptions and shared keys)
        if not found:
            root_logic = _find_root_logic(tool_logic_path)
            if root_logic and root_logic != tool_logic_path:
                root_trans = root_logic / "translation" / f"{lang}.json"
                if root_trans.exists():
                    try:
                        with open(root_trans, 'r', encoding='utf-8') as f:
                            root_data = json.load(f)
                            result = root_data.get(key)
                            if result:
                                translated_text = result
                                found = True
                    except Exception:
                        pass
    
    # 5. Handle recursive translation with {{}}
    # We find all {{...}} patterns and replace them with their own translations
    if translated_text:
        def replace_recursive(match):
            recursive_key = match.group(1)
            # Call get_translation recursively on the same directory
            return get_translation(tool_logic_dir, recursive_key, recursive_key, lang_code=lang)

        # Use a regex to find {{key}}
        translated_text = re.sub(r'\{\{([^}]+)\}\}', replace_recursive, translated_text)
    
    # 6. Handle standard formatting with {} if kwargs are provided
    if translated_text and kwargs:
        try:
            return translated_text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
            
    return translated_text
