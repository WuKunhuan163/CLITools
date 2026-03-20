# GOOGLE.GS — Agent Quick Reference

## When to Use
Use GOOGLE.GS when you need to:
- Search academic papers on Google Scholar
- Get citation data (BibTeX, MLA, APA, etc.) for a paper
- Find papers that cite a specific paper
- Discover author profiles and their publications
- Save papers to the user's Google Scholar library
- Get PDF download URLs for papers

## CLI Commands

| Command | Description |
|---------|-------------|
| `GS boot` | Boot Scholar session |
| `GS search <query> [--year-from N] [--year-to N]` | Search papers |
| `GS results` | Re-read current results |
| `GS next` / `GS prev` | Navigate pages |
| `GS open --index N` | Open paper link |
| `GS save --index N` | Save paper to library |
| `GS cite --index N` | Get citation formats |
| `GS cited-by --index N` | Find citing papers |
| `GS pdf --index N` | Get PDF URL |
| `GS filter --time YEAR` | Filter by year |
| `GS filter --sort date` | Sort by date |
| `GS profile` | View user's profile |
| `GS library` | View saved papers |
| `GS author <name>` | Search author profiles |
| `GS state` | Get MCP state |
| `GS screenshot [--output path]` | Take screenshot |

## Typical Workflow

```bash
# 1. Boot session (if not already running)
GS boot

# 2. Search
GS search "attention mechanism transformer"

# 3. Get citation for the top result
GS cite --index 0

# 4. Get PDF link
GS pdf --index 0

# 5. Explore citing papers
GS cited-by --index 0

# 6. Find a specific author
GS author "Yoshua Bengio"
```

## Return Value Format

All API functions return dicts with `ok` boolean:
```json
{"ok": true, "results": [...], "count": 10}
{"ok": false, "error": "No session"}
```

Search result objects:
```json
{
  "index": 0, "title": "...", "link": "https://...",
  "authors": "...", "snippet": "...",
  "cited": "Cited by 234175", "cited_href": "...",
  "pdf_url": "https://...", "pdf_label": "[PDF] neurips.cc"
}
```

## Notes
- Results are 0-indexed (first result = index 0)
- Session auto-boots on first operation if not already running
- All operations use CDMCP visual effects (lock, badge, highlight)
- The tool reuses the existing `scholar` CDMCP session
