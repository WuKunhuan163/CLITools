# LINTER - Multi-language Linter and Code Analyzer

## Overview

LINTER is a comprehensive tool that provides:
1. **Multi-language Syntax Checking**: Python, JavaScript, TypeScript, Java, C/C++, SQL, JSON, YAML, HTML, CSS, Shell scripts
2. **Python Code Analysis**:
   - Unused code detection
   - Import validation
   - Function signature checking

## Features

### Syntax Checking
- Automatic language detection from file extensions
- Manual language override with `--language` option
- Multiple output formats (text or JSON)
- Comprehensive error detection

### Python Code Analysis
1. **Unused Code Detection**
   - AST-based static analysis (no code execution required)
   - Detects unused functions, classes, variables, and imports
   - Distinguishes public and private definitions
   - Supports single files or entire directories

2. **Import Validation**
   - Detects unused imports
   - Identifies missing imports
   - Validates import statements

3. **Function Signature Checking**
   - Validates function call arguments
   - Checks parameter counts and types
   - Handles default parameters and keyword arguments
   - Detects signature mismatches

All analysis tools support both text and JSON output formats

## Installation Requirements

### For Syntax Checking

The tool automatically detects available linters. Install these for best results:

#### Python
- `flake8` (recommended): `pip install flake8`
- `pylint`: `pip install pylint`
- `pycodestyle`: `pip install pycodestyle`

#### JavaScript/TypeScript
- `eslint`: `npm install -g eslint`
- `jshint`: `npm install -g jshint`

#### Other Languages
- `shellcheck`: `brew install shellcheck` (Shell scripts)
- `yamllint`: `pip install yamllint` (YAML)
- `jsonlint`: `npm install -g jsonlint` (JSON)
- `sqlfluff`: `pip install sqlfluff` (SQL)

### For Unused Code Detection

No additional dependencies required - uses Python's built-in AST module.

## Usage

### Syntax Checking

```bash
# Check a Python file
LINTER lint file.py

# Check with language override
LINTER lint file.txt --language python

# Get JSON output
LINTER lint file.py --format json

# Legacy usage (still supported)
LINTER file.py
```

### Python Code Analysis

#### Unused Code Detection

```bash
# Analyze a single Python file
LINTER unused google_drive_shell.py

# Analyze entire directory
LINTER unused GOOGLE_DRIVE_PROJ/

# Get JSON output
LINTER unused GOOGLE_DRIVE_PROJ/ --format json

# Verbose output with progress
LINTER unused GOOGLE_DRIVE_PROJ/ --verbose
```

#### Import Validation

```bash
# Check imports in a file
LINTER imports file.py

# Check imports in directory
LINTER imports GOOGLE_DRIVE_PROJ/

# JSON output
LINTER imports GOOGLE_DRIVE_PROJ/ --format json
```

#### Function Signature Checking

```bash
# Check function signatures in a file
LINTER signature file.py

# Check signatures in directory
LINTER signature GOOGLE_DRIVE_PROJ/

# JSON output
LINTER signature GOOGLE_DRIVE_PROJ/ --format json
```

## Output Examples

### Syntax Checking (Text Format)

```
Language: python
Status: FAIL
Linter: Python linting with flake8

1 issues found:
ERROR: file.py:9:19: E999 SyntaxError: '(' was never closed
```

### Unused Code Detection (Text Format)

```
Target: GOOGLE_DRIVE_PROJ/
Files analyzed: 56
Status: PASS
Unused items found: 451

Functions: 378
  GOOGLE_DRIVE_PROJ/cache_manager.py
    Line 36: GDSCacheManager.load_cache_config [private]
    Line 49: GDSCacheManager.cleanup_cache 
    ... and 374 more

Classes: 38
  ...
```

### JSON Format

Both commands support `--format json` for programmatic use:

```json
{
  "success": true,
  "message": "Analyzed 56 files, found 451 unused items",
  "total_files": 56,
  "total_unused": 451,
  "unused": {
    "functions": [
      ["path/to/file.py", 36, "function_name", false]
    ]
  }
}
```

## Command Reference

### Main Commands

- `LINTER lint <file> [options]` - Check file syntax/style
- `LINTER unused <path> [options]` - Detect unused Python code
- `LINTER imports <path> [options]` - Check Python imports
- `LINTER signature <path> [options]` - Check function signatures
- `LINTER --help` - Show help message
- `LINTER --version` - Show version

### Options

#### For `lint` command:
- `--language`, `-l` - Override language detection
- `--format`, `-f` - Output format: `text` or `json` (default: text)

#### For `unused`, `imports`, `signature` commands:
- `--format`, `-f` - Output format: `text` or `json` (default: text)
- `--verbose`, `-v` - Show progress during analysis

## Understanding Unused Code Results

### Markers

- `[private]` - Private definitions (starting with `_`), may be intentionally internal
- No marker - Public definitions that could potentially be removed

### Important Notes

1. **Static Analysis Limitations**: May have false positives for:
   - Dynamically called functions (e.g., `getattr()`)
   - Decorator-registered functions
   - Meta-class magic methods
   - Framework-specific patterns (Django models, Flask routes, etc.)

2. **Special Methods**: The analyzer automatically excludes:
   - Magic methods (`__init__`, `__str__`, etc.)
   - Common exports (`__all__`, `__version__`, etc.)
   - Main function guard code

3. **Verification**: Always verify unused code manually before deletion. Consider:
   - Is it part of a public API?
   - Is it called dynamically?
   - Is it used by external code?

## Architecture

```
.local/bin/
├── LINTER              # Executable wrapper script
├── LINTER.py           # Main entry point
├── LINTER.md           # Documentation
└── LINTER_PROJ/        # Project directory
    └── modules/
        ├── unused_code_detector.py  # Unused code analysis
        ├── import_checker.py        # Import validation
        └── signature_checker.py     # Function signature checking
```

The project follows a clean structure:
- Root directory contains the main executable (`LINTER`), main script (`LINTER.py`), and documentation
- `LINTER_PROJ/` contains detailed implementation modules
- Each analysis feature is implemented as a separate module
- New analysis modules can be added to `LINTER_PROJ/modules/`

## Integration Examples

### Use in CI/CD

```bash
# Check all Python files have valid syntax
find . -name "*.py" -exec LINTER lint {} \;

# Generate unused code report
LINTER unused src/ --format json > unused-report.json
```

### Programmatic Use

```python
import subprocess
import json

# Run unused code analysis
result = subprocess.run(
    ['LINTER', 'unused', 'myproject/', '--format', 'json'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
print(f"Found {data['total_unused']} unused items")
```

## Version History

### Version 2.0.0
- Added Python code analysis tools:
  - Unused code detection
  - Import validation
  - Function signature checking
- Modular architecture with separate analysis modules
- Improved output formatting (clean, concise)
- Better error handling
- JSON output support for all commands

### Version 1.0.0
- Initial release
- Multi-language syntax checking
- JSON output support

## Contributing

The tool is designed to be extensible. To add new features:

1. Create a new module in `LINTER_PROJ/modules/`
2. Import and integrate in `LINTER.py`
3. Add command-line interface in the main argument parser
4. Update this documentation

## License

This tool is part of the local development environment utilities.
