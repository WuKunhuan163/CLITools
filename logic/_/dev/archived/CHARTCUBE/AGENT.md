# ChartCube MCP — Agent Guide

## Overview

CHARTCUBE automates AntV ChartCube (`chartcube.alipay.com`) via CDMCP. No authentication required. The tool provides a 4-step chart creation workflow: upload data → select chart → configure → export.

## Architecture

- **Base class**: `MCPToolBase` from `logic.base.blueprint.mcp`
- **CDP layer**: `logic.chrome.session.CDPSession` for page-level WebSocket communication
- **Session management**: `logic.cdmcp_loader` → `GOOGLE.CDMCP` session manager
- **Overlays**: Badge ("ChartCube MCP"), favicon (purple "C"), focus indicator
- **Session name**: `chartcube`

### Boot Sequence

1. `boot_tool_session("chartcube")` — creates/reuses a CDMCP session (shared window with other CDMCP tools)
2. `session.require_tab("chartcube", url_pattern="chartcube.alipay.com", open_url=HOME)` — opens ChartCube tab
3. `CDPSession(tab_ws)` — connects to the tab's page-level WebSocket (cached per process)
4. Overlays applied, then clicks "立即制作图表" to enter the wizard (if on home page)

### Critical: SPA Routing

ChartCube is a React SPA. Direct navigation to `/upload`, `/guide`, `/make`, `/export` returns 404. The wizard MUST be entered from the home page (`/`) by clicking the "立即制作图表" button. The `boot` command handles this automatically.

## Typical Workflow for Agents

```bash
CHARTCUBE boot                    # Opens session + navigates to /upload
CHARTCUBE columns all             # Select all data columns (or specific: "x,y")
CHARTCUBE next                    # → Step 2: Select Chart
CHARTCUBE chart 折线图            # Click chart card → auto-navigates to Step 3
# Configure chart properties
CHARTCUBE title "月度销售趋势"
CHARTCUBE toggle 平滑             # Enable smooth curves
CHARTCUBE toggle 显示点           # Show data points
CHARTCUBE size 800 500            # Set canvas to 800x500px
CHARTCUBE generate                # → Step 4: Export
CHARTCUBE get-code                # Extract G2Plot code
```

### Step-by-Step Details

**Step 1 — Upload Data (`/upload`)**
- Default: sample data selected (`sample-1`)
- Select columns using `CHARTCUBE columns all` (or `columns x,y` for specific)
- Columns are displayed as checkboxes: 全部, series, x, y, z
- "下一步" button is DISABLED until at least 1 column is selected

**Step 2 — Select Chart (`/guide`)**
- 30+ chart types across 11 categories (折线图类, 柱状图类, 条形图类, 饼图类, 面积图类, 散点图类, 热力图类, 雷达图类, 点图层类, 面图层类, 其他类)
- Use `CHARTCUBE chart <name>` with exact Chinese name (e.g. `折线图`, `柱状图`, `饼图`, `散点图`)
- Use `CHARTCUBE list-charts` to enumerate all types (must be on /guide page)
- Clicking a chart card auto-navigates to Step 3 (no separate Next button needed)

**Step 3 — Configure Chart (`/make`)**
- **Canvas**: `CHARTCUBE size <w> <h>` (default 560x376)
- **Title**: `CHARTCUBE title <text>`
- **Description**: `CHARTCUBE description <text>`
- **Checkbox options** (vary by chart type):
  - 折线图: `toggle 平滑`, `toggle 显示点`, `toggle 显示标签`
  - 饼图: `toggle 显示标签`
  - 柱状图: `toggle 显示标签`
- Use `CHARTCUBE generate` to click "完成配置，生成图表" → navigates to Step 4

**Step 4 — Export Chart (`/export`)**
- Export sections: 图片 (Image), 数据 (Data), 代码 (Code), 配置文件 (Config)
- `CHARTCUBE export-all` clicks "全部导出" button
- `CHARTCUBE export code` clicks "复制代码" (triggers Ant Design toast "Copy to clipboard" — this is the site's own clipboard write using `document.execCommand('copy')`, not a browser-native dialog)
- **Preferred for agents**: `CHARTCUBE get-code` — extracts the G2Plot code directly from the `<code>` DOM element via CDP (no clipboard dependency)
- `CHARTCUBE get-config` — extracts the full chart config JSON from the second `<code>` block

## DOM Notes

- Framework: React + Ant Design (`ant-btn`, `ant-select`, `ant-radio`, `ant-checkbox`, `ant-steps`)
- Data table: Handsontable (`handsontable` class, `hot-*` IDs)
- Chart cards: `.chart-view` class
- Step indicator: `.ant-steps-item-process` (active), `.ant-steps-item-wait` (pending)
- Buttons: `ant-btn ant-btn-primary` for main actions
- Column checkboxes: `label.ant-checkbox-wrapper` with text matching column names

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry, `MCPToolBase("CHARTCUBE")`, argparse, command dispatch |
| `logic/chrome/api.py` | All CDP operations: boot, status, navigate, click, evaluate |
| `data/exploration/chartcube_elements.json` | Complete DOM exploration record |

## Development Lessons (2026-03-05)

### CDMCP integration pattern
Use `boot_tool_session()` from the session manager (not manual `create_session` + `boot`). This enables session reuse across tools sharing the same Chrome window. The pattern is: `boot_tool_session` → `session.require_tab()` → `CDPSession(tab_info["ws"])`.

### SPA routing pitfall
React SPAs like ChartCube return 404 on direct URL navigation. Always navigate to the app root first and use programmatic button clicks to enter inner pages. Test by checking `document.title` (not just URL) to confirm the page loaded correctly.

### CDPSession WebSocket exclusivity
Chrome allows exactly one page-level WebSocket connection per target. When the CDMCP session manager holds an attachment (`Target.getTargets` shows `attached=True`), direct `CDPSession(ws_url)` connections will time out. Cache CDPSession per-process and explicitly `.close()` old connections before creating new ones.

### Disabled button investigation
When a button click has no effect, check `button.disabled` via CDP evaluate before assuming the click failed. Many Ant Design forms disable action buttons until required fields are filled. Use `scan` command to inspect element states.

## Known Limitations

- CDPSession caching: Chrome allows one page-level WebSocket per target. CDPSession is cached per process to prevent conflicts with session manager attachments.
- Export page: Some export buttons may require additional handling due to clipboard API restrictions in CDP mode.
- SPA navigation: Cannot bookmark or deep-link to wizard steps.
