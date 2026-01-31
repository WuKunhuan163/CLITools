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

## 3. Word (.docx) Extraction
Uses **python-docx** to iterate through paragraphs and extract relationships (images).

## 4. Cache and Output Management
- **Dynamic Directories**: Each extraction creates a unique `result_YYYYMMDD_HHMMSS_HASH/` folder.
- **Centralized Cache**: Limits the number of stored results to 1024, automatically cleaning the oldest 512 when the limit is reached.

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
