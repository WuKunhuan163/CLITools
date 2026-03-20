# CHARTCUBE — ChartCube Chart Generation via CDMCP

Access AntV [ChartCube](https://chartcube.alipay.com) online charting tool via CDMCP (Chrome DevTools MCP). ChartCube is a public, no-auth-required chart creation wizard powered by AntV/G2.

## Architecture

CHARTCUBE uses the `MCPToolBase` and CDMCP infrastructure (`GOOGLE.CDMCP`) to automate the ChartCube web application via Chrome DevTools Protocol. The tool:

1. Boots a CDMCP session with visual overlays (badge, favicon, focus indicator)
2. Opens ChartCube in a managed Chrome tab within the session window
3. Navigates the 4-step wizard via JavaScript evaluation over CDP WebSocket
4. Each CLI command is a standalone process that reconnects to the CDMCP session

### Key Dependencies

- `GOOGLE.CDMCP` — session management, overlays, tab lifecycle
- `websocket-client` — Chrome DevTools Protocol communication
- `logic.chrome.session.CDPSession` — lightweight CDP WebSocket wrapper

## 4-Step Wizard Workflow

| Step | Name | Path | Key Action |
|------|------|------|------------|
| 1 | Upload Data (上传数据) | `/upload` | Select sample/local data, choose columns |
| 2 | Select Chart (选择图表) | `/guide` | Click a chart card (30+ types) |
| 3 | Configure Chart (配置图表) | `/make` | Adjust canvas, legend, data, properties |
| 4 | Export Chart (导出图表) | `/export` | Export as image, data, code, or config |

**Important**: ChartCube is a React SPA. Direct URL navigation to `/upload` etc. results in 404. The wizard must be entered from the home page via the "立即制作图表" button (handled automatically by `boot`).

## Commands

### Session & Navigation
```
CHARTCUBE boot               # Boot CDMCP session, open ChartCube
CHARTCUBE status              # Show current wizard step
CHARTCUBE page                # Show page title, buttons, headings
CHARTCUBE scan                # Scan interactive elements with positions
CHARTCUBE start               # Click '立即制作图表' from home page
CHARTCUBE go <step>           # Navigate: upload, guide, make, export, home
CHARTCUBE session             # Show CDMCP session status
CHARTCUBE state               # Get comprehensive MCP state
```

### Step 1: Upload Data
```
CHARTCUBE sample [0|1|2]      # Select sample dataset on upload page
CHARTCUBE columns [all|x,y]   # Select data columns (required before Next)
CHARTCUBE next                # Click '下一步' button
```

### Step 2: Select Chart
```
CHARTCUBE chart <name>        # Select chart type (e.g. '柱状图', '折线图', '饼图')
CHARTCUBE list-charts         # List all available chart types (must be on guide page)
```

### Step 3: Configure Chart
```
CHARTCUBE title <text>        # Set chart title
CHARTCUBE description <text>  # Set chart description
CHARTCUBE size <w> <h>        # Set canvas size (e.g. 800 500)
CHARTCUBE toggle <option>     # Toggle checkbox (平滑, 显示点, 显示标签)
CHARTCUBE generate            # Click '完成配置，生成图表'
```

### Step 4: Export
```
CHARTCUBE export [all|image|data|code|config]
CHARTCUBE export-all          # Click '全部导出' button
CHARTCUBE get-code            # Extract G2Plot code from DOM (no clipboard)
CHARTCUBE get-config          # Extract chart config JSON from DOM
```

### Quick E2E Example

```bash
CHARTCUBE boot
CHARTCUBE columns all
CHARTCUBE next
CHARTCUBE chart 折线图
# Configure
CHARTCUBE title "月度销售趋势"
CHARTCUBE toggle 平滑
CHARTCUBE toggle 显示点
CHARTCUBE size 800 500
CHARTCUBE generate
# Extract output
CHARTCUBE get-code
CHARTCUBE get-config
```

## Chart Types

| Category | Charts |
|----------|--------|
| 折线图类 | 折线图, 阶梯图 |
| 柱状图类 | 柱状图, 分组柱状图, 堆叠柱状图, 百分比堆叠柱状图, 瀑布图, 直方图 |
| 条形图类 | 条形图, 分组条形图, 堆叠条形图, 百分比堆叠条形图 |
| 饼图类 | 饼图, 环图 |
| 面积图类 | 面积图, 堆叠面积图, 百分比堆叠面积图 |
| 散点图类 | 散点图, 气泡图 |
| 热力图类 | 连续热力图, 热力图, 不均匀热力图 |
| 雷达图类 | 雷达图 |
| 点图层类 | 气泡地图, 亮点地图 |
| 面图层类 | 世界地图, 中国地图-省级, 中国地图-市级 |
| 其他类 | 水波图 |

## File Structure

```
tool/CHARTCUBE/
├── main.py                          # CLI entry point (MCPToolBase)
├── setup.py                         # Tool installation
├── tool.json                        # Metadata + dependencies
├── logic/
│   ├── chrome/
│   │   └── api.py                   # CDMCP operations (boot, navigate, evaluate)
├── data/
│   └── exploration/
│       └── chartcube_elements.json  # DOM exploration findings
├── README.md
└── AGENT.md
```
