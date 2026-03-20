---
name: report-conventions
description: Development report conventions for AITerminalTools. Covers naming, structure, namespacing, CLI integration, and how to record development insights with minimal overhead for ecosystem packaging.
---

# Report Conventions

Reports capture development insights at the time they happen. They are lightweight, date-stamped Markdown files that serve as a project's institutional memory — useful for debugging, auditing, and packaging the project for delivery.

## When to Write a Report

| Trigger | Example |
|---------|---------|
| Significant investigation completed | "Analyzed Chrome CDP session lifecycle" |
| Architecture decision made | "Chose SSE over WebSocket for assistant GUI" |
| Audit or quality review done | "Code audit found 12 dead code blocks" |
| Integration explored | "Explored Baidu ERNIE API compatibility" |
| Debugging session with findings | "Root cause: race condition in hook loading" |

**When NOT to write a report:** Routine code changes, simple bug fixes, documentation updates. These go in git commit messages and BRAIN log entries.

## Naming Convention

```
YYYY-MM-DD_topic-slug.md
```

- **Date prefix**: ISO 8601, always present — ensures chronological ordering
- **Topic slug**: Lowercase kebab-case, max 60 characters
- **Extension**: Always `.md`

Examples:
- `2026-03-15_assistant-token-reduction.md`
- `2026-03-16_assistant-code-audit.md`
- `2026-03-17_cursor-ide-internals.md`

## Directory Structure

```
report/                      # Root: cross-cutting reports
├── README.md                # Directory documentation
├── openclaw/                # Namespace: OPENCLAW-related reports
├── tool/                    # Namespace: tool-specific reports
│   └── vpn_exploration_READ.md
└── <namespace>/             # Add more as needed
```

### Scope/Namespace Rules

| Scope | Location | When to Use |
|-------|----------|-------------|
| Root | `report/` | Cross-cutting, ecosystem-wide topics |
| Tool-specific | `report/tool/` or `tool/<NAME>/data/report/` | Single-tool investigations |
| Namespace | `report/<namespace>/` | Topic-grouped series (e.g., `openclaw/`) |

## CLI Integration

The `logic/_/dev/report.py` module provides programmatic access:

```python
from logic._.dev.report import create_report, list_reports, view_file

path = create_report("root", "my-investigation", content)
reports = list_reports("root")
text = view_file("root", "2026-03-15_my-investigation.md")
```

### Keeping Overhead Low

Reports should be **easy to create and hard to forget**:

1. **Auto-date**: `create_report()` auto-generates the date prefix — no manual formatting
2. **Auto-scope**: CLI resolves scope strings to paths — no path construction
3. **Template-free**: Just write Markdown, no required frontmatter or structure
4. **At natural breakpoints**: Write reports during USERINPUT feedback loops, not as a separate task

### Minimal Report Template

```markdown
# Topic Title

**Date**: YYYY-MM-DD
**Context**: What prompted this investigation

## Findings

- Key finding 1
- Key finding 2

## Impact

What changed as a result (code, architecture, documentation).

## References

- Relevant files: `path/to/file.py`
- Related reports: `report/YYYY-MM-DD_related.md`
```

## For Context-Free Agents

A new agent needs to understand the report system in 30 seconds:

1. **Discovery**: `report/README.md` explains the directory
2. **Listing**: `TOOL --report list` shows all reports chronologically
3. **Creation**: `create_report(scope, topic, content)` — no ceremony
4. **Guideline**: This skill teaches when and how to report

The agent should develop a habit: after completing a significant task, check if the findings warrant a report. If the investigation took >30 minutes or revealed non-obvious insights, write a report.

## Integration with Ecosystem

### With BRAIN

```bash
BRAIN log "Completed investigation, report at report/2026-03-15_topic.md"
```

BRAIN log entries are ephemeral activity records. Reports are persistent documents. When a BRAIN log entry describes something worth preserving, elevate it to a report.

### With USERINPUT

During USERINPUT feedback, the hint can reference a report:
```bash
USERINPUT --hint "Investigation complete. Report: report/2026-03-15_topic.md"
```

### With TEX (Future)

When TEX is available, reports can be compiled to PDF for formal delivery:
```bash
TEX compile report/2026-03-15_topic.md --output report/pdf/
```

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Reports without date prefix | Always use `create_report()` which auto-dates |
| Mixing reports with source code | Reports go in `report/`, not alongside `.py` files |
| Overly detailed reports for trivial changes | Use git commits and BRAIN log instead |
| No reports for significant investigations | Develop the habit: >30 min investigation → report |
| Reports scattered across arbitrary directories | Use scoped namespaces in `report/` |
