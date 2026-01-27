# TEX Tool

Local LaTeX compilation and project bootstrapping.

## Features

- **Local Compilation**: Compile `.tex` files to PDF without needing an account on Overleaf.
- **Project Templates**: Start new research papers with industry-standard templates (ACM, IEEE, Nature, Science, NeurIPS).
- **Collision Management**: Automatically avoids overwriting existing directories by adding a random hash suffix.
- **Symmetrical Design**: Part of the `TOOL` ecosystem with standardized command handling.

## Usage

### List Available Templates
```bash
TEX list
```

### Create Project from Template
```bash
TEX template ACM --target ./my_paper
```

### Compile to PDF
```bash
TEX compile main.tex --output ./build
```

## Installation

This tool depends on `pdflatex`. If not found in your system's PATH, you can run:
```bash
TEX setup
```
to install a lightweight local TeX distribution (TinyTeX).

