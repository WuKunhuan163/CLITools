# Font Migration and Management Report

## Overview
This report outlines the strategy for migrating, naming, and managing font resources within the `AITerminalTools` ecosystem, specifically for use by the `READ` and `FONT` tools.

## Migration Strategy
Font resources are collected from academic papers and external repositories (e.g., FontsGeek, Google Fonts, Monaspace). The migration process involves several steps to ensure consistency and usability.

### 1. Resource Collection
- Fonts are initially downloaded as ZIP files or individual OTF/TTF files into `tmp/fontsgeek/`.
- The user provides ZIPs in this directory, which the `FONT` tool then processes.

### 2. Normalization and Naming
Standardization of font names is critical for reliable retrieval. We use the following rules:
- **Case**: All font names and filenames are converted to lowercase.
- **Separators**: All spaces, underscores, and special characters are replaced with a single hyphen (`-`).
- **Standard Suffixes**: Names are simplified to represent the family and weight (e.g., `arnhem-blond`, `arial-mt-bold`).
- **Format**: All deployed fonts are standardized to `.ttf` format.

### 3. Format Conversion (OTF to TTF)
Since many PDF tools and libraries (like `fpdf2` and some versions of `reportlab`) have better support for TrueType (`.ttf`) than OpenType (`.otf`) with PostScript outlines, we convert all OTF files to TTF during migration.
- **Tool**: We use `fontTools.ttLib` and `fontTools.fontBuilder`.
- **Process**:
    1. Read the OTF file.
    2. Setup TrueType structures.
    3. Save as a `.ttf` file in the destination directory.

### 4. Deployment Structure
Fonts are deployed to `resource/fonts/<normalized-name>/`.
Each directory contains:
- `<normalized-name>.ttf`: The primary font file.
- `heuristics.json`: (Generated later) Contains glyph metrics and bounding box heuristics for precise character identification.

## Naming Convention Examples
| Original Name | Normalized Name |
| :--- | :--- |
| ArnhemBlond | `arnhem-blond` |
| Arnhem Blond Regular | `arnhem-blond-regular` |
| ArialMT | `arial-mt` |
| OpenSans-BoldItalic | `open-sans-bold-italic` |

## Heuristics Calculation
For each deployed font, the `FONT` tool (or associated scripts) generates a character table PDF to analyze:
- **Glyph BBox**: The theoretical bounding box provided by the font metrics.
- **Actual BBox**: The precise bounding box of the rendered pixels.
- **Heuristics**: Normalized values (left, right, top, bottom) that describe the relationship between the glyph bbox and the actual pixel content. These are stored in `heuristics.json`.

## Future Work
- Automation of `heuristics.json` generation upon migration.
- Support for variable fonts.
- Improved fallback mapping for missing weights.


