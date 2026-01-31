# READ Tool Implementation Principles

## 1. Overview
The `READ` tool is designed to help AI agents understand various document formats (PDF, Word, Images) by converting them into clean, structured Markdown. This allows the AI to "read" papers and reports with their original layout and visual elements preserved.

## 2. PDF Extraction (Basic Mode)
The basic mode uses **PyMuPDF (fitz)** for high-performance extraction.

### 2.1 Advanced Layout Analysis
Instead of simple top-to-bottom extraction, the `READ` tool uses a modular `ReadingOrderSorter` to handle complex academic layouts:
- **Header/Footer Detection**: Identifies content in the top and bottom 10% of the page.
- **Vertical Zone Segmentation**: Detects blocks that span across the entire page (like titles or full-width figures) and uses them as separators.
- **Sub-column Detection**: Within body zones, it uses X-coordinate clustering to identify multiple columns and sorts them left-to-right, then top-to-bottom.

### 2.2 Font and Style Awareness
`READ` leverages PyMuPDF's detailed span information to detect styles:
- **Bold**: Detected via font flags and font name inspection (`**text**`).
- **Italic**: Detected via font flags and font name inspection (`*text*`).
- **Subscripts/Superscripts**: Detected by comparing font size with the page median and checking the vertical origin relative to the baseline (`<sub>text</sub>` / `<sup>text</sup>`).
- **Smart Line Joining**: Merges lines within a paragraph while maintaining separation between distinct sections.

### 2.3 Image Handling
Images are extracted in their original resolution, hashed for deduplication, and saved to a dedicated `images/` directory within the result folder. Placeholders are inserted into the Markdown to indicate their original position.

## 3. Semantic Identification and Visualization
The `READ` tool identifies semantic blocks (title, heading, paragraph, image, header, footer) and generates two visual aids:
- **`source.png`**: A high-resolution (2x zoom) screenshot of the original page.
- **`extracted.png`**: The same screenshot with semi-transparent color overlays and outlines highlighting each identified semantic block.

### 3.1 Identification Heuristics
- **Title**: Blocks with font size significantly larger (>1.5x) than the page median.
- **Heading**: Blocks with slightly larger font size (>1.1x).
- **Header/Footer**: Blocks located in the extreme top (<8%) or bottom (>92%) margins.
- **Image**: Detected via PDF object metadata.

## 4. Word (.docx) and Image Extraction
- **Word**: Uses **python-docx** to iterate through paragraphs and extract images.
- **Images**: Integrated vision analysis using Gemini API (with free/paid fallback) to describe subjects and extract text/code.

## 5. Output and Cache Management
- **Structured Pages**: Each page is saved in its own `pages/page_XXX/` directory containing:
  - `extracted.md`: Markdown with style-aware text and HTML comments for block tracking.
  - `extracted.png`: Visual semantic overlay.
  - `source.pdf` / `source.png`: Original page references.
  - `images/`: Page-specific raster images.
- **Centralized Cache**: Limits the number of stored results to 1024, automatically cleaning the oldest 512.

## 5. Comparison with Other Tools
| Feature | READ (Basic) | MinerU / MinerU-like |
|---------|--------------|----------------------|
| **Speed** | Very Fast (ms) | Slower (seconds/minutes) |
| **Dependencies** | Minimal | Heavy (Deep Learning models) |
| **Accuracy** | High for standard layouts | Superior for extremely complex layouts |
| **OCR Support** | No (future) | Yes |

## 6. Future Improvements
- **OCR Integration**: For scanned PDFs.
- **Image Analysis**: Use Gemini/OpenRouter to describe extracted images.
- **Table Reconstruction**: Better conversion of PDF tables to Markdown tables.
