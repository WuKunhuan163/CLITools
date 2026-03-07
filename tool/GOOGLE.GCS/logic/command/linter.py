#!/usr/bin/env python3
"""GCS linter command: lint remote files locally."""
import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path

LANGUAGE_MAP = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.json': 'json', '.java': 'java', '.cpp': 'cpp', '.c': 'c',
    '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
    '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell',
}

LINTER_MAP = {
    'python': 'pyflakes', 'javascript': 'eslint', 'json': 'json',
    'shell': 'shellcheck',
}


def execute(tool, args, state_mgr, load_logic, unknown=None, **kwargs):
    utils = load_logic("utils")

    lint_args = unknown or []
    if not lint_args:
        print("linter: missing operand", file=sys.stderr)
        return 1

    if "--help" in lint_args or "-h" in lint_args:
        _show_help()
        return 0

    language = None
    filename = None
    i = 0
    while i < len(lint_args):
        if lint_args[i] == "--language" and i + 1 < len(lint_args):
            language = lint_args[i + 1]
            i += 2
        else:
            if filename is None:
                filename = lint_args[i]
            i += 1

    if not filename:
        print("linter: missing file operand", file=sys.stderr)
        return 1

    folder_id, fname, display = utils.resolve_file_path(
        tool.project_root, filename, state_mgr, load_logic
    )
    if not folder_id:
        print(f"linter: {filename}: {fname}", file=sys.stderr)
        return 1

    ok, data = utils.read_file_via_api(tool.project_root, folder_id, fname)
    if not ok:
        print(f"linter: {filename}: {data.get('error', 'Cannot read file')}", file=sys.stderr)
        return 1

    content = data.get("content", "")
    result = lint_content(content, filename, language)

    lang = result.get("language", "unknown")
    has_errors = bool(result.get("errors", []))
    status = "FAIL" if has_errors else "PASS"

    from interface.config import get_color
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    status_color = RED if has_errors else GREEN
    print(f"Language: {BOLD}{lang}{RESET}")
    print(f"Status: {BOLD}{status_color}{status}{RESET}")
    print(f"Message: {result.get('message', '')}")

    errors = result.get("errors", [])
    if errors:
        print(f"\n{BOLD}{RED}Errors:{RESET}")
        for e in errors:
            print(f"  {e}")

    warnings = result.get("warnings", [])
    if warnings:
        from logic.turing.status import fmt_warning
        for w in warnings:
            print(fmt_warning(w, indent=0))

    return 1 if errors else 0


def detect_language(filename, language=None):
    if language:
        return language.lower()
    ext = Path(filename).suffix.lower()
    return LANGUAGE_MAP.get(ext, 'unknown')


def lint_content(content, filename, language=None):
    detected = detect_language(filename, language)

    if detected == 'unknown':
        return {"language": detected, "message": f"Language not detected for {filename}, skipping",
                "errors": [], "warnings": []}

    if detected not in LINTER_MAP:
        return {"language": detected, "message": f"No linter available for {detected}",
                "errors": [], "warnings": []}

    linter = LINTER_MAP[detected]
    return _run_linter(content, filename, detected, linter)


def _run_linter(content, filename, language, linter):
    try:
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if language == 'python':
                return _lint_python(tmp_path, linter)
            elif language == 'json':
                return _lint_json(tmp_path)
            elif language == 'shell':
                return _lint_shell(tmp_path)
            elif language in ('javascript', 'typescript'):
                return _lint_js(tmp_path, linter)
            else:
                return {"language": language, "message": f"Linter not implemented for {language}",
                        "errors": [], "warnings": []}
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        return {"language": language, "message": f"Linting failed: {e}",
                "errors": [str(e)], "warnings": []}


def _lint_python(file_path, linter):
    errors, warnings = [], []
    try:
        if linter == 'pyflakes':
            result = subprocess.run(['pyflakes', file_path], capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(['python3', '-m', 'py_compile', file_path], capture_output=True, text=True, timeout=30)

        output = (result.stderr or "") + (result.stdout or "")
        if result.returncode != 0:
            for line in output.strip().split('\n'):
                if line.strip():
                    if any(k in line for k in ('SyntaxError', 'IndentationError', 'invalid syntax')):
                        errors.append(line.strip())
                    elif line.startswith('  File '):
                        errors.append(line.strip())
                    else:
                        warnings.append(line.strip())
        elif result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    warnings.append(line.strip())
    except FileNotFoundError:
        result = subprocess.run(['python3', '-m', 'py_compile', file_path], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            errors.append((result.stderr or result.stdout or "Syntax error").strip())

    return {"language": "python", "message": f"Python linting completed with {linter}",
            "errors": errors, "warnings": warnings}


def _lint_json(file_path):
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return {"language": "json", "message": "JSON is valid",
                "errors": [], "warnings": []}
    except json.JSONDecodeError as e:
        return {"language": "json", "message": "JSON syntax error",
                "errors": [f"Line {e.lineno}: {e.msg}"], "warnings": []}


def _lint_shell(file_path):
    try:
        result = subprocess.run(['shellcheck', file_path], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return {"language": "shell", "message": "No issues found",
                    "errors": [], "warnings": []}
        errors = [l.strip() for l in result.stdout.split('\n') if l.strip()]
        return {"language": "shell", "message": "Shellcheck found issues",
                "errors": errors, "warnings": []}
    except FileNotFoundError:
        return {"language": "shell", "message": "shellcheck not installed",
                "errors": [], "warnings": ["shellcheck not available"]}


def _lint_js(file_path, linter):
    try:
        result = subprocess.run(['eslint', '--format=compact', file_path], capture_output=True, text=True, timeout=30)
        errors, warnings = [], []
        for line in (result.stdout + result.stderr).strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                else:
                    warnings.append(line.strip())
        return {"language": "javascript", "message": f"JS linting completed with {linter}",
                "errors": errors, "warnings": warnings}
    except FileNotFoundError:
        return {"language": "javascript", "message": "eslint not installed",
                "errors": [], "warnings": ["eslint not available"]}


def _show_help():
    print("""linter - lint remote files locally

Usage:
  GCS linter <file> [--language <lang>]

Arguments:
  file                     Remote file path

Options:
  --language <lang>        Override language detection
  -h, --help               Show this help message

Supported Languages:
  Python  (.py)   - pyflakes
  JSON    (.json) - json.load validation
  Shell   (.sh)   - shellcheck
  JS/TS   (.js/.ts) - eslint

Examples:
  GCS linter ~/tmp/script.py              Lint Python file
  GCS linter ~/config.json                Validate JSON
  GCS linter ~/run.sh                     Lint shell script
  GCS linter ~/app.js --language javascript   Override language""")
