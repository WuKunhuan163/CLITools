# READ Tool Implementation (Basic Mode)

## Overview
The current implementation of the `READ` tool is a "basic" extraction mode, primarily based on the logic from `EXTRACT_PDF`'s basic engine. It is designed to provide fast, reliable content extraction from PDF and Word documents without heavy external dependencies like MinerU.

## PDF Extraction Principles
The PDF extraction uses `PyMuPDF` (fitz) and follows these steps:

1.  **Page Selection**: Parses user-provided page specifications (e.g., "1,3,5-7") to target specific content.
2.  **Image Extraction**: 
    - Identifies all image objects on each page.
    - Extracts raw image data and converts it to PNG (handling CMYK to RGB conversion if needed).
    - Generates a unique hash-based filename for each image to avoid duplicates.
    - Places a `[placeholder: image]` tag in the markdown output followed by the absolute path to the extracted image.
3.  **Text Extraction**: 
    - Retrieves text blocks from the page using `get_text("blocks")`.
    - **Advanced Reading Order Algorithm**: To handle complex two-column paper layouts, the tool uses a multi-stage sorting heuristic:
        1.  **Position-Based Header/Footer Detection**: Blocks in the top 10% or bottom 10% of the page are identified as potential headers/footers and prioritized for start/end placement.
        2.  **Vertical Zone Segmentation**: The remaining body is divided into vertical zones by identifying "spanning" blocks (those spanning >60% of the page width, like wide figures or section headers).
        3.  **X-Coordinate Clustering**: Within each body zone, sub-columns (like the nested columns in a References section) are detected by clustering blocks with similar horizontal alignments.
        4.  **Sequential Merging**: Blocks are then merged in order: Headers -> (Top-to-Bottom Zones, each sorted Left-to-Right Column) -> Footers.
    - **Smart Linebreak Handling**: Uses a heuristic based on ending punctuation to smartly merge lines, ensuring fluid sentences while respecting paragraph breaks.
4.  **Organized Output**:
    - Creates a timestamped and hash-identified directory in `data/pdf/`.
    - Saves the final content as `text.md`.
    - Saves all extracted images in an `images/` sub-directory.

## Word (.docx) Extraction Principles
The Word extraction uses `python-docx`:

1.  **Paragraph Processing**: Iterates through all paragraphs in the document, preserving text content.
2.  **Image Extraction**: Scans document relationships for image parts and extracts them, similar to the PDF process.

## Performance & Optimization
- **Execution Speed**: The basic mode is extremely fast (typically < 1s for a single page) as it doesn't perform complex OCR or layout analysis.
- **Cache Management**: Automatically manages the `data/pdf/` directory, keeping up to 1024 results and cleaning the oldest half when the limit is reached.
- **Organized Output**: Each extraction is saved in a unique directory (`result_date_time_hash/`) containing `text.md` and an `images/` folder. This facilitates easy integration with other tools.
- **Precise Timing**: Extraction time is reported with 2 decimal places for better performance monitoring.

## Comparison with MinerU
Unlike the advanced MinerU engine, this basic mode:
- Does **not** perform layout-aware table reconstruction (tables are extracted as raw text).
- Does **not** recognize LaTeX formulas (formulas are extracted as text or images).
- Does **not** perform high-level structural analysis (e.g., identifying headers vs. body text beyond basic formatting).

## Future Improvements
- **Formula & Table Placeholders**: Integrate with `UNIMERNET` to specifically identify and tag formulas/tables for better post-processing.
- **Image Analysis**: Automatically trigger `IMG2TEXT` for extracted images to provide natural language descriptions within the markdown.
- **Layout Awareness**: Improve structural detection (headers, footers, multi-column text) using bounding box heuristics from `PyMuPDF`.

