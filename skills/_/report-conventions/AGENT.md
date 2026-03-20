# Report Conventions — Agent Guide

## Quick Actions

| Task | How |
|------|-----|
| Create a report | `from logic._.dev.report import create_report; create_report("root", "topic", content)` |
| List reports | `from logic._.dev.report import list_reports; list_reports("root")` |
| View a report | `from logic._.dev.report import view_file; view_file("root", "filename.md")` |

## When to Write

After any investigation >30 minutes that revealed non-obvious findings. At natural breakpoints (USERINPUT feedback loops). When making architecture decisions.

## Naming

Always use `create_report()` — it auto-generates `YYYY-MM-DD_topic.md` format. Never manually construct filenames.

## Scoping

- `"root"` → `report/` (cross-cutting)
- `"report/openclaw"` → `report/openclaw/` (namespaced)
- `"tool/LLM"` → `tool/LLM/data/report/` (tool-specific, internal)
