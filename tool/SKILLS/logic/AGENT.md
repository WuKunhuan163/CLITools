# SKILLS Logic — Technical Reference

## evolution.py

OpenClaw-inspired self-improvement loop:
- `record_lesson(text)`: Append to `runtime/experience/lessons.jsonl`
- `list_lessons()`: Read all lessons
- `analyze_lessons()`: Review lessons for patterns and actionable insights
- `generate_suggestions()`: Propose skill/rule improvements
- `apply_suggestion(id)`: Apply a suggestion (create/update skill or rule)
- `get_history()`: Read evolution history

`BRAIN_DIR` points to `runtime/experience/` (project root).

## marketplace.py

ClawHub marketplace integration:
- `list_sources()`: Available marketplace sources
- `browse_clawhub()`: List skills from ClawHub API
- `search_clawhub(query)`: Search ClawHub skills
- `fetch_clawhub_skill(slug)`: Download skill via `/api/v1/download` (zip)
- `convert_to_skill_md(content)`: Convert external skill to SKILL.md format
- `install_skill(slug, target_dir)`: Download and install to local skills directory
- `uninstall_skill(slug, target_dir)`: Remove installed marketplace skill

Download flow: ClawHub API -> zip download -> extract SKILL.md + supporting files.

## introspect (evolution.py)

Analyzes recent agent transcripts for behavior patterns:
- Scans JSONL transcript files from `~/.cursor/projects/Applications-*/agent-transcripts/`
- Counts tool mentions, error keywords, and message statistics
- Generates improvement opportunities based on patterns (fix frequency, error rates, timeout issues)
- Returns structured report with tool mentions, error patterns, and actionable suggestions

## Gotchas

1. **curl fallback**: `_http_get_bytes` falls back to curl subprocess if urllib fails (rate limiting).
2. **BRAIN_DIR path**: Computed relative to file location — 4 parents up to project root, then `runtime/experience/`.
3. **Marketplace cache**: Stored at `runtime/experience/marketplace_cache.json`, refreshed on each browse/search.
