# FONT Logic

Font management and analysis. Downloads, deploys, and analyzes fonts with bounding box heuristics for layout analysis.

## Structure

| Module | Purpose |
|--------|---------|
| `engine.py` | `FontManager` — font download, installation, mapping from Google Fonts/resources |
| `bbox_analyzer.py` | `BBoxAnalyzer` — character bounding box analysis, PDF generation, heuristic output |
