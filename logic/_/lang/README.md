# logic/lang

Internationalization and language audit: translation lookup, LangAuditor, ImportAuditor, and language commands.

## Contents

- **utils.py** - `get_translation(tool_logic_dir, key, default_text, lang_code, **kwargs)` - Supports `{{recursive_key}}` and `{literal_key}`
- **audit.py** - `LangAuditor` - Scans keys in code, checks translation coverage, Turing stage audit
- **audit_imports.py** - `ImportAuditor`, `audit_tool`, `audit_all_tools` - Cross-tool import rules, CDMCP usage
- **commands.py** - `audit_lang`, `list_languages` - CLI entry points for lang audit

## Structure

```
lang/
  __init__.py
  utils.py
  audit.py
  audit_imports.py
  commands.py
```
