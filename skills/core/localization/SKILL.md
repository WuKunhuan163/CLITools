---
name: localization
description: Multi-language localization system for AITerminalTools. Covers translation file layout, the _() helper, and audit workflows.
---

# Localization

## Translation File Layout

```
tool/<NAME>/logic/translation/
    zh.json       # Chinese
    ja.json       # Japanese
    ko.json       # Korean
    ...
```

No `en.json` -- English is always the fallback default embedded in code.

## The `_()` Helper

```python
from logic.interface.lang import get_translator

_ = get_translator("TOOL_NAME")

print(_("greeting", "Hello, world!"))       # Returns translated or "Hello, world!"
print(_("count_msg", "Found {n} items", n=5))  # Supports format args
```

### Rules
- First argument: translation key (snake_case)
- Second argument: English default string (ALWAYS required)
- Named format args pass through to `.format()`

## Adding Translations

1. Create `tool/<NAME>/logic/translation/<lang>.json`:

```json
{
  "greeting": "Translation here",
  "count_msg": "Found {n} items (translated)"
}
```

2. Keys must match those used in `_()` calls.

## Audit Workflow

```bash
TOOL lang audit                    # Audit all tools
TOOL lang audit --tool <NAME>      # Single tool
TOOL lang audit --turing           # With progress display
```

The audit checks:
- All `_()` calls in source have corresponding keys in each translation file
- No orphan keys in translation files (keys not used in code)
- No format-arg mismatches between code and translations

## Guidelines

1. Wrap ALL user-facing strings with `_()`, including error messages and help text
2. Keep keys descriptive and stable (renaming keys breaks translations)
3. Test with `LANG=zh TOOL_NAME --help` to verify translations load
4. Use the audit before releases to catch missing translations
