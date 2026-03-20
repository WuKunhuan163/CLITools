# TEX

Report compilation tool for AITerminalTools. Converts Markdown reports to PDF.

## Usage

```bash
TEX compile report/2026-03-15_topic.md          # Compile to PDF
TEX compile report/2026-03-15_topic.md --output ./  # Custom output dir
TEX list                                          # List root reports
TEX list openclaw                                 # List namespaced reports
TEX template                                      # Show report template
```

## Output

PDFs are generated in `report/pdf/` by default.

## Dependencies

- `markdown` — Markdown to HTML conversion
- `weasyprint` — HTML to PDF rendering (requires system dependencies)

## Future

Full LaTeX support via tectonic or texlive for advanced typesetting.
