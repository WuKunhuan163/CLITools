# CHARTCUBE Logic — Technical Reference

## Architecture

Session-based CDMCP tool following XMIND pattern:
```
boot_session() -> boot_tool_session() -> require_tab -> CDPSession(ws)
```

ChartCube is a step-by-step wizard UI. The API maps to wizard navigation + chart configuration.

## chrome/api.py

Workflow automation:
1. `boot_session()` -> `start_chart()` -> `select_chart_type()`
2. `use_sample_data()` or upload data -> `select_columns()`
3. `generate_chart()` -> `set_title()`, `set_description()`, `toggle_option()`
4. `export_chart()`, `export_all()`, `get_code()`, `get_config()`

Navigation: `navigate_step()`, `click_next()` to move between wizard pages.

Utility: `scan_elements()` for DOM discovery, `list_chart_types()` for available types.

## Gotchas

1. **Wizard-based UI**: Operations must follow the wizard flow (data -> type -> configure -> export). Calling export before generate will fail.
2. **Alipay domain**: `chartcube.alipay.com` — may require Chinese network access.
