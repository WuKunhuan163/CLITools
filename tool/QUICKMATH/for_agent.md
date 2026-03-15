# QUICKMATH -- Agent Guide

Quick arithmetic calculator for basic operations.

## Commands

```bash
QUICKMATH add 3 5          # → 8.0
QUICKMATH subtract 10 4    # → 6.0
QUICKMATH multiply 6 7     # → 42.0
QUICKMATH divide 20 4      # → 5.0
QUICKMATH batch "3+5, 10-4, 6*7"
```

## Parameters

All arithmetic commands take two positional arguments: `A` and `B`.

## Error Handling

- Division by zero returns an error message.
- Invalid numbers produce a parse error.

## Notes

- Results are printed as floats.
- `batch` uses Python's `eval()` for simple expressions.
