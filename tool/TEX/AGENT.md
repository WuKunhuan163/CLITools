# TEX — Agent Guide

## Commands

| Command | Purpose |
|---------|---------|
| `TEX compile <file.md>` | Convert Markdown to PDF |
| `TEX list [scope]` | List available reports |
| `TEX template` | Show report template |

## Integration

TEX compiles reports from `report/` using `logic/_/dev/report.py` infrastructure. Reports follow `YYYY-MM-DD_topic.md` naming convention.

## Current Limitations

- Uses markdown + weasyprint (not LaTeX)
- weasyprint requires system-level dependencies (cairo, pango)
- No LaTeX math or advanced typesetting yet
