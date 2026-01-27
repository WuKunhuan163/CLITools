# SEARCH Tool

Multi-platform search tool for web and academic papers. Part of the `TOOL` ecosystem.

## Features

- **Web Search**: General web results powered by DuckDuckGo.
- **Academic Search**: Parallel search across arXiv and Google Scholar.
- **Advanced Filtering**: Filter academic results by minimum citations and publication year.
- **Sorting**: Multi-criteria sorting (relevance, citations, title, date).
- **Exact Match**: Support for literal phrase search via quotes.

## Usage

### Web Search
```bash
SEARCH "Python programming"
SEARCH "Quantum computing" --max 10
```

### Paper Search
```bash
SEARCH --paper "Large Language Models"
SEARCH --paper "Machine Learning" --source arxiv --sort citations,date
SEARCH --paper "Deep Learning" --min-citations 100 --min-year 2020
```

## Options

- `<query>`: Search query (use quotes for exact match).
- `--max, -m`: Maximum results to return (default: 5).
- `--paper, -p`: Enable academic paper search.
- `--source`: Sources for papers (comma-separated: `arxiv`, `scholar`).
- `--sort`: Sort criteria (comma-separated: `relevance`, `citations`, `title`, `date`).
- `--min-citations`: Minimum citations for paper results.
- `--min-year`: Minimum publication year.
- `--exact, -e`: Enforce exact phrase match.

## Architecture

- **`main.py`**: CLI entry point and orchestration.
- **`logic/paper/searcher.py`**: Paper search logic and scrapers.
- **`tool.json`**: Dependency metadata (requires `PYTHON`).
- **`data/results/`**: Search history saved in JSON format.

