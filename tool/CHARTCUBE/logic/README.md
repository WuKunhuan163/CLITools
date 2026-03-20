# CHARTCUBE Logic

ChartCube (Alipay) chart generation via CDMCP. Automates the chartcube.alipay.com web app to create, configure, and export charts.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — chart creation, configuration, export |

## API Functions

| Function | Purpose |
|----------|---------|
| `boot_session()` | Create CDMCP session |
| `start_chart()` | Begin new chart workflow |
| `select_chart_type()` | Choose chart type (bar, line, pie, etc.) |
| `use_sample_data()` | Load sample dataset |
| `select_columns()` | Pick data columns for axes |
| `generate_chart()` | Render the chart |
| `set_title()` / `set_description()` | Configure chart metadata |
| `set_canvas_size()` | Set export dimensions |
| `toggle_option()` | Enable/disable chart features |
| `export_chart()` / `export_all()` / `get_code()` | Export as image, get embed code |
| `navigate_step()` / `click_next()` | Navigate wizard steps |
