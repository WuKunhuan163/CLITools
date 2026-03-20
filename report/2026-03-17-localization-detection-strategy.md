# Localization Detection Strategy

## Problem

CLI tools and the HTML assistant UI contain hardcoded user-facing strings that should be localized via the `_()` helper but aren't. Currently, `TOOL --audit --lang <code>` audits translation *coverage* (keys that exist vs. keys used), but cannot detect strings that were **never wrapped** in `_()` in the first place.

## Enterprise Solutions Surveyed

| Tool | Language | Approach | Relevance |
|------|----------|----------|-----------|
| **Globalyzer** (Lingoport) | Multi-language | Commercial scanner, commit/PR integration, historical tracking | Gold standard but proprietary |
| **i18nGuard** | TypeScript/JS | AST-based detection in JSX/TSX, VS Code integration, SARIF reporting | Good model for JS-side detection |
| **eslint-plugin-no-hardcoded-strings** | JS/JSX | ESLint rule forbidding hardcoded strings in JSX | Pattern we can replicate for Python |
| **python-pylint-i18n** | Python (Django) | Pylint checker for non-i18n strings | Closest to our needs |
| **i18n-check** | JSON keys | JSON key/value validation, placeholder checks | Already covered by our LangAuditor |
| **l10n-audit-toolkit** | Multi-framework | Cross-framework scanning, terminology audit | Report format ideas |
| **IntelliJ i18n inspection** | Java/Kotlin | IDE-native hardcoded string detection with quick-fix extraction | Inspiration for detection heuristics |

## Proposed Detection Strategy for AITerminalTools

### Tier 1: Python CLI Strings (Turing Machine, status messages)

**Approach**: AST-based detection using Python's `ast` module.

Scan for:
1. **`print()` calls** containing string literals or f-strings with user-facing text
2. **`sys.stdout.write()`** with hardcoded strings
3. **f-string fragments** inside format expressions (`f"...{BOLD}text{RESET}..."`)
4. **TuringStage parameters** — `active_status`, `success_status`, `fail_status` that use raw strings instead of `_()`

Heuristics to filter false positives:
- Skip strings that are purely ANSI codes, punctuation, or whitespace
- Skip strings inside `# comments`
- Skip strings assigned to `__doc__`, `__all__`, variable names
- Skip log messages (`logger.debug()`, `log_debug()`)
- Flag strings containing CJK characters paired with English identifiers (mixed-language)
- Flag strings > 3 alphabetic characters that aren't wrapped in `_()`

### Tier 2: HTML GUI Strings

**Approach**: DOM text content analysis + JS string literal detection.

Scan for:
1. **HTML text content** — `<span>`, `<button>`, `<label>`, `<h1-6>`, `<p>` elements with hardcoded text
2. **JavaScript string literals** — `textContent =`, `innerText =`, `innerHTML =` assignments with user-facing strings
3. **Template literals** in JS — backtick strings with user-facing text
4. **Placeholder attributes** — `placeholder="..."`, `title="..."`, `aria-label="..."`

### Tier 3: Turing Machine States (Already Implemented)

The existing `audit_turing()` in `LangAuditor` already covers TuringStage parameters. Extend to also flag raw string literals in stage definitions.

## Implementation Plan

### Phase 1: Python CLI String Detector

Create `logic/_/lang/detect.py` with:
- `StringDetector` class using `ast.NodeVisitor`
- Detection rules for `print()`, `sys.stdout.write()`, f-strings
- Heuristic filtering (skip non-user-facing strings)
- Report generation: file, line, string content, suggested key name

### Phase 2: HTML/JS String Detector

Create `logic/_/lang/detect_html.py` with:
- HTML parser for text content extraction
- JS string literal scanner
- Integration with the main audit command

### Phase 3: Integration

- Add `--detect` flag to `TOOL --audit --lang` command
- Output format: file:line — hardcoded string — suggested `_("key", "default")`
- Auto-fix mode: wrap detected strings in `_()` calls

## Detection Heuristics (Critical for Low False Positives)

### Strings to SKIP (not user-facing):
- Import paths, module names
- Dictionary keys, JSON field names
- ANSI escape codes
- File paths, URLs
- Regex patterns
- Variable names, identifiers
- Empty strings, single characters
- Strings inside `__all__`, `__doc__`
- Debug/log messages
- Test assertions

### Strings to FLAG (likely user-facing):
- Arguments to `print()`, `sys.stdout.write()`
- F-string fragments containing words
- String literals in TuringStage `*_status` or `*_name` params
- Strings assigned to variables named `msg`, `message`, `label`, `title`, `desc`, `help`
- Strings in `argparse` `help=` parameters

## Metrics

- **Precision target**: >80% (at most 20% false positives)
- **Recall target**: >60% initially, improving with heuristic tuning
- Coverage report format matches existing `audit_lang` output
