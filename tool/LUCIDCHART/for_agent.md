# Lucidchart MCP - Agent Guide

## Setup

1. Ensure CDMCP session is running: `GOOGLE.CDMCP --mcp-boot`
2. Boot Lucidchart: `LUCIDCHART --mcp-boot`
3. If not logged in, the tool auto-attempts Google SSO login

## Key Workflows

### Creating a Diagram

```bash
LUCIDCHART --mcp-boot
LUCIDCHART --mcp-navigate home
LUCIDCHART --mcp-open-doc "Blank diagram"
LUCIDCHART --mcp-add-shape "Process" --x 400 --y 300
LUCIDCHART --mcp-escape
LUCIDCHART --mcp-add-shape "Decision" --x 550 --y 300
LUCIDCHART --mcp-escape
LUCIDCHART --mcp-add-shape "Terminator" --x 700 --y 300
LUCIDCHART --mcp-screenshot --output /tmp/diagram.png
```

### Available Shapes

Use `LUCIDCHART --mcp-shapes` to list all draggable shapes. Common ones:
- Flowchart: Process, Decision, Terminator, Document, Data (I/O), Database
- Basic: Rectangle, Circle, Star, Diamond, Triangle, Arrow
- Standard: Text, Block, Sticky note, Line, Frame, Code block

### Editor Interaction Pattern

1. Always `--mcp-escape` before adding a new shape (to deselect previous)
2. Use `--mcp-click <x> <y>` to select shapes or click empty canvas
3. Canvas coordinates are screen-absolute (use `--mcp-layout` to get canvas bounds)
4. After adding shapes, use `--mcp-screenshot` to verify placement

### Navigation Targets

`--mcp-navigate` accepts: home, documents, templates, recent, shared, trash, or any URL

### Tab Behavior

Lucidchart opens documents in new tabs. The tool automatically:
- Detects editor tabs (URLs containing `/lucidchart/` and `/edit`)
- Prefers editor tabs over document browser tabs
- Injects badge/favicon/lock overlays on new editor tabs

### Limitations

- WebGL canvas: shapes are rendered on canvas, not as DOM elements
- `--mcp-select-all` may not work if canvas lacks focus; click empty area first
- Free plan limits: no team library, limited exports, watermarks
- Document creation opens new tab; check `--mcp-page` after `--mcp-new`

## CLI Reference

```
LUCIDCHART --mcp-boot|--mcp-session|--mcp-recover|--mcp-status|--mcp-page|--mcp-state|--mcp-layout
LUCIDCHART --mcp-navigate <target>|--mcp-back|--mcp-new|--mcp-open <url>|--mcp-open-doc <name>
LUCIDCHART --mcp-templates [category]|--mcp-documents [--limit N]
LUCIDCHART --mcp-select-all|--mcp-delete|--mcp-copy|--mcp-paste|--mcp-undo|--mcp-redo
LUCIDCHART --mcp-group|--mcp-ungroup|--mcp-escape
LUCIDCHART --mcp-zoom [in|out|fit|reset]|--mcp-zoom-level
LUCIDCHART --mcp-add-shape <name> [--x X --y Y]
LUCIDCHART --mcp-add-text <text> [--x X --y Y]
LUCIDCHART --mcp-click <x> <y>|--mcp-draw-line <x1> <y1> <x2> <y2>
LUCIDCHART --mcp-fill-color <hex>|--mcp-toolbar <title>|--mcp-rename <name>
LUCIDCHART --mcp-pages|--mcp-add-page|--mcp-shapes|--mcp-shape-libraries
LUCIDCHART --mcp-screenshot [--output path]
```
