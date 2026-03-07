# GUI Translation Files

JSON files for GUI string localization. Keys are shared across blueprints and resolved via `get_translation(internal_dir, key, default)` in `logic.lang.utils`.

## Structure

- `ar.json`: Arabic translations
- `zh.json`: Chinese translations (currently empty; placeholder for future)

## Key Conventions

- Keys match those used in blueprint `_()` calls (e.g., `time_remaining`, `btn_cancel`, `add_time`).
- Fallback: tool-specific `internal_dir` first, then `logic/gui/translation` via project root.
- Format placeholders use `{name}` (e.g., `add_time`: "Add {seconds}s").

## Adding Translations

Add a new `{locale}.json` file with key-value pairs. Ensure keys align with defaults in blueprint code.
