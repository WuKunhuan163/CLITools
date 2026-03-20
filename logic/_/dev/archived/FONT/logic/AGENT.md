# FONT Logic — Technical Reference

## engine.py — FontManager

```python
FontManager(project_root)
```

- `resource_dir`: `logic/_/dev/resource/FONT/data/install/` — bundled font archives
- `mapping_file`: `tool/FONT/logic/font_mapping.json` — font name to file mapping
- Downloads fonts from Google Fonts or extracts from bundled resources
- Installs to system font directories

## bbox_analyzer.py — BBoxAnalyzer

```python
BBoxAnalyzer(font_path, output_dir, font_name=None)
```

- Renders characters using the font and measures bounding boxes
- Generates PDF reports with visual bounding box overlays
- Uses PyMuPDF (fitz), fpdf, PIL, and numpy
- Outputs JSON heuristics for layout analysis

## Gotchas

1. **Heavy dependencies**: Requires numpy, fitz (PyMuPDF), fpdf, PIL. Check `tool.json` for dependency list.
2. **font_mapping.json**: Located in `logic/` (code directory), not `data/`. This is a static mapping, not runtime data.
