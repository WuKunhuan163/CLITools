# logic/tool/template — Agent Reference

## How It Works

`logic.dev.commands._load_template(filename, **kwargs)` reads a `.tmpl` file and calls `.format(**kwargs)` to fill placeholders.

Templates use Python `str.format()` syntax:
- `{name}` -> tool name
- `{short_name}` -> CLI-facing name (last dot-segment)
- `{{BOLD}}` -> literal `{BOLD}` (escaped for f-string compatibility in generated code)

## Adding New Templates

1. Create `<filename>.tmpl` in this directory
2. Use `{name}` and `{short_name}` as placeholders
3. Escape literal braces as `{{` and `}}`
4. Call `_load_template("<filename>.tmpl", name=..., short_name=...)` in `dev_create()`

## Gotchas

1. **Double-brace escaping**: Templates use `str.format()`, so any literal `{` or `}` in generated code (like f-string expressions) must be `{{` and `}}`.
2. **Template directory path**: `_TEMPLATE_DIR` in `commands.py` resolves to `logic/tool/template/` relative to the commands module.
