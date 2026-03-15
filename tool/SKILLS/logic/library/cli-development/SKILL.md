---
name: cli-development
description: Command-line tool development patterns. Use when working with cli development concepts or setting up related projects.
---

# CLI Development

## Core Principles

- **Exit Codes**: 0 for success, non-zero for errors
- **Stderr for Errors**: Output goes to stdout, errors to stderr
- **Unix Philosophy**: Do one thing well; compose with pipes
- **Help Text**: Always include `--help` with usage examples

## Python (argparse)
```python
parser = argparse.ArgumentParser(description="Process files")
parser.add_argument("input", help="Input file path")
parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("--format", choices=["json", "csv"], default="json")
args = parser.parse_args()
```

## Python (click)
```python
@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", default="-", help="Output file")
@click.option("--verbose", "-v", is_flag=True)
def process(input_file, output, verbose):
    """Process INPUT_FILE and write results."""
```

## Best Practices
- Support both `--long-flag` and `-s` short flags
- Use colors sparingly (respect `NO_COLOR` env var)
- Show progress bars for long operations
- Support piping (`stdin`/`stdout`)
- Provide machine-readable output (`--json` flag)

## Error Handling
```python
try:
    result = process(args.input)
except FileNotFoundError:
    print(f"Error: File not found: {args.input}", file=sys.stderr)
    sys.exit(1)
```
