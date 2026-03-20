# logic/translation

Root-level translation files for the framework. Keys are looked up by `logic.lang.utils.get_translation` when `tool_logic_dir` points to this directory.

## Contents

- **zh.json** - Chinese translations
- **ar.json** - Arabic translations

## Structure

```
translation/
  zh.json
  ar.json
```

## Format

JSON object: `{"key": "value"}`. Supports `{placeholder}` for formatting and `{{recursive_key}}` for nested lookup.
