# logic/lang - Agent Reference

> **Import convention**: Tools should import from `interface.lang` (the facade), not directly from `logic.lang`. See `interface/AGENT.md`.

## Key Interfaces

### utils.py
- `get_translation(tool_logic_dir, key, default_text, lang_code=None, **kwargs)` - Looks up in `translation/{lang}.json` or `translation.json`; resolves `{{key}}` recursively; formats `{key}` with kwargs
- Language: `TOOL_LANGUAGE` env, `get_global_config("language")`, default "en"

### audit.py
- `LangAuditor(project_root, lang_code)` - `audit(force_scan)` returns (results, cached); `audit_turing()` for TuringStage state injection report
- Scans: `_("key")`, `get_translation(..., "key")`, `print_metric("key")`
- Output: missing keys, duplicate values/keys, shadowed keys, unused translations, en violations
- `_cleanup_unused` removes unused keys from JSON files

### audit_imports.py
- `ImportAuditor` - AST visitor; rules: IMP001 (cross-tool via interface), IMP002 (raw CDP tab ops), IMP003 (cdmcp_loader), IMP004 (MCPToolBase)
- `audit_tool(tool_dir, project_root)` - Returns list of ImportIssue
- `audit_all_tools(project_root, exclude)` - Returns {tool_name: [issues]}
- `format_report(results)`, `to_json(results)`

### commands.py
- `audit_lang(lang_code, project_root, force, turing, translation_func)` - Runs LangAuditor, prints summary
- `list_languages(project_root, translation_func)` - Table of supported langs with coverage

## Usage Patterns

1. **Translation**: `_ = lambda k, d, **kw: get_translation(logic_dir, k, d, **kw)` then `_("key", "default", name=val)`
2. **Audit**: `audit_lang("zh", project_root, force=True)` for full scan
3. **Import audit**: `audit_all_tools(project_root)` then `format_report(results)`

## Gotchas

- `tool_logic_dir` is typically `get_logic_dir(project_root)` or tool's logic dir
- LangAuditor excludes venv, .git, build, data, etc.
- IMP001: cross-tool must use `tool.X.interface.main`
- IMP003: use `logic.cdmcp_loader`, not hardcoded CDMCP paths
