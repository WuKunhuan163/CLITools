---
name: development-report
description: Writing development reports for AITerminalTools. Covers naming, content structure, and code citation for Markdown reports stored in tool data/report/ directories.
---

# Development Report Writing

## Location

Reports are stored per-tool:

```
tool/<NAME>/data/report/
    YYYY-MM-DD_topic.md        # Date-prefixed report
```

## Content Structure

```markdown
# Report Title

## Summary
Brief 1-2 sentence overview of what was done.

## Changes Made
- **File**: `path/to/file.py`
  - Description of change
  - Why this change was necessary

## Issues Found & Fixed
1. **Issue**: Description
   - **Root cause**: Why it happened
   - **Fix**: What was done
   - **Lesson**: What to remember

## Testing
- What was tested and how
- Results

## Next Steps
- Remaining work items
```

## Code Citation

When referencing code in reports, use the standard format:

```
path/to/file.py:L42-L58 - Description of this section
```

## Naming Convention

- Use ISO date prefix: `2026-03-05_session_recovery.md`
- Topic should be concise and descriptive
- One report per logical unit of work

## Guidelines

1. Write reports for non-trivial work sessions
2. Focus on decisions and trade-offs, not just what was done
3. Include error descriptions with root causes
4. Link to related lessons (`SKILLS lessons --tool <NAME>`)
