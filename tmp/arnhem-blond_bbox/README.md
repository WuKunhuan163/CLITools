# Arnhem Blond BBox Investigation

## Purpose
This project aims to investigate the discrepancy between the logical bounding boxes (Glyph BBox) reported by font metrics and the actual pixel boundaries (Actual BBox) when rendered. Discrepancies can lead to unintended overlaps with background elements (like lines) in layout analysis.

## Font Source
The font used is **Arnhem Blond**.
Source: [FontsGeek - Arnhem Blond](https://fontsgeek.com/fonts/arnhem-blond/download) (automatic download triggered on page browse).

## Methodology
1.  **Source Generation**: A character table (`source.pdf`) is generated containing all printable ASCII characters.
2.  **Extraction**: The PDF is rendered at zoom 2.0 to `source.png`.
3.  **BBox Comparison**:
    -   `glyph_bbox.png`: Overlays the theoretical bboxes (red) reported by the PDF extractor.
    -   `actual_bbox.png`: Overlays the actual pixel bounds (blue) detected via intensity analysis.
4.  **Metadata**: `info.json` maps each bbox back to its character or block type to identify any "strange" elements.

## Visualization Key
-   **Red Rectangles**: Glyph BBox (theoretical).
-   **Blue Rectangles**: Actual BBox (pixel-based).
-   **Green Rectangles**: Block BBox.
-   **Yellow Rectangles**: Line BBox.

## How to Run
```bash
python3 analyze.py
```
(Requires `fitz`, `fpdf`, `PIL`, `numpy`)

