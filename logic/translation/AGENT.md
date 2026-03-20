# logic/translation - Agent Reference

## Key Interfaces

### zh.json, ar.json
- Flat key-value; keys match `_("key", "default")` and `get_translation(..., "key", default)` in code
- Placeholders: `{name}`, `{count}`, etc. for `.format(**kwargs)`
- Recursive: `{{other_key}}` resolved by get_translation

## Usage Patterns

1. Add key: Ensure key exists in code first; add to translation JSON
2. Lang audit: `audit_lang("zh", project_root)` reports missing keys
3. Tool-specific: Tools can have `tool/X/logic/translation/zh.json`; overrides root for that tool's logic dir

## Gotchas

- English is default; no en.json needed for root
- `list_languages` discovers langs from `logic/translation/*.json` filenames
