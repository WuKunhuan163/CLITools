# Report

Development reports, audit results, and analysis documents. Organized by namespace (subdirectories) for scoped topics.

## Structure

```
report/
├── README.md                           # This file
├── 2026-03-15_assistant-token-reduction.md  # Root-level reports (general/cross-cutting)
├── openclaw/                           # Namespace: OPENCLAW analysis reports
├── tool/                               # Namespace: tool-specific reports
└── <namespace>/                        # Add namespaces as needed
```

## Naming Convention

Reports use date-prefixed names: `YYYY-MM-DD_topic-slug.md`

- Date prefix ensures chronological ordering
- Topic slug uses lowercase kebab-case, max 60 chars
- Extension is always `.md` (Markdown)

## CLI Commands

```bash
TOOL --report list                      # List all reports
TOOL --report list --scope openclaw     # List reports in namespace
TOOL --report create "topic" --scope root  # Create a new report
TOOL --report view <filename>           # View a report
```

## When to Write a Report

- After completing a significant development task or investigation
- When analyzing a system gap, audit finding, or architectural decision
- When exploring a new technology or integration approach
- When documenting a debugging session with findings

Reports are lightweight — they capture insights at the time of development. They are **not** formal documentation (that goes in README.md/AGENT.md).

## For Agents

Use `logic/_/dev/report.py` functions:
- `create_report(scope, topic, content)` — auto-generates date prefix
- `list_reports(scope)` — lists reports by scope
- `view_file(scope, filename)` — reads a report
