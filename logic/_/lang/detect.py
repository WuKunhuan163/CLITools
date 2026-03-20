"""Hardcoded string detector for Python source files.

Uses AST analysis to find user-facing strings that are not wrapped in _().
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


SKIP_DIRS = {"venv", ".git", "build", "dist", "tmp", "installations", "install",
             "node_modules", "bin", "archived", "resource", "data", "site-packages", "__pycache__"}

_ANSI_RE = re.compile(r'^\\033\[|^\033\[|^\\x1b\[|^\x1b\[')
_PATH_RE = re.compile(r'^[/.]|\\|\.py$|\.json$|\.md$|\.txt$')
_URL_RE = re.compile(r'^https?://|^ftp://|^file://')
_IDENTIFIER_RE = re.compile(r'^[a-z_][a-z0-9_]*$')

USER_FACING_VAR_NAMES = {"msg", "message", "label", "title", "desc", "description",
                          "help_text", "hint", "prompt", "status", "error_msg",
                          "warning_msg", "header", "footer", "caption"}


def _is_likely_user_facing(s: str) -> bool:
    """Heuristic: is this string likely shown to users?"""
    if not s or len(s.strip()) < 3:
        return False
    stripped = s.strip()
    if _ANSI_RE.match(stripped):
        return False
    if _PATH_RE.match(stripped):
        return False
    if _URL_RE.match(stripped):
        return False
    if _IDENTIFIER_RE.match(stripped):
        return False
    alpha_count = sum(1 for c in stripped if c.isalpha())
    if alpha_count < 3:
        return False
    if stripped.startswith("{") and stripped.endswith("}"):
        return False
    if all(c in ".-_/\\*?[](){}|" for c in stripped):
        return False
    return True


def _extract_string_value(node) -> Optional[str]:
    """Extract string value from an AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                parts.append("{...}")
        return "".join(parts)
    return None


class StringDetector(ast.NodeVisitor):
    """AST visitor that detects hardcoded user-facing strings not wrapped in _()."""

    def __init__(self, filepath: Path, project_root: Path):
        self.filepath = filepath
        self.project_root = project_root
        self.findings: List[Dict[str, Any]] = []
        self._in_translation_call = False
        self._source_lines: List[str] = []

    def _add(self, line: int, string_val: str, context: str):
        if _is_likely_user_facing(string_val):
            self.findings.append({
                "file": str(self.filepath.relative_to(self.project_root)),
                "line": line,
                "string": string_val[:120],
                "context": context,
            })

    def _is_in_skip_context(self, node) -> bool:
        """Check if we're inside a context where strings are not user-facing."""
        return self._in_translation_call

    def visit_Call(self, node: ast.Call):
        func = node.func
        func_name = ""
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute):
            func_name = func.attr

        if func_name == "_" or func_name == "get_translation":
            old = self._in_translation_call
            self._in_translation_call = True
            self.generic_visit(node)
            self._in_translation_call = old
            return

        skip_funcs = {"log_debug", "debug", "warning", "info", "error",
                       "getattr", "setattr", "isinstance", "issubclass",
                       "hasattr", "open", "Path", "compile", "match",
                       "search", "sub", "replace", "format", "join",
                       "startswith", "endswith", "split", "strip",
                       "encode", "decode", "ImportError", "ValueError",
                       "KeyError", "FileNotFoundError", "TypeError",
                       "RuntimeError", "AttributeError", "Exception",
                       "mkdir", "exists", "glob", "rglob",
                       "add_argument", "add_parser"}
        if func_name in skip_funcs:
            return

        if func_name == "print":
            for arg in node.args:
                self._check_print_arg(arg, node.lineno)
            return

        if func_name in ("write", "stdout"):
            for arg in node.args:
                self._check_print_arg(arg, node.lineno)
            return

        if func_name == "TuringStage":
            for kw in node.keywords:
                if kw.arg in ("active_status", "success_status", "fail_status",
                              "active_name", "success_name", "fail_name"):
                    s = _extract_string_value(kw.value)
                    if s and not self._is_call_to_translate(kw.value):
                        self._add(node.lineno, s, f"TuringStage.{kw.arg}")
            self.generic_visit(node)
            return

        self.generic_visit(node)

    def _check_print_arg(self, node, lineno):
        """Check a print() argument for hardcoded strings."""
        if self._in_translation_call:
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            self._add(lineno, node.value, "print()")
        elif isinstance(node, ast.JoinedStr):
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    s = v.value.strip()
                    if _is_likely_user_facing(s):
                        self._add(lineno, s, "f-string in print()")

    def _is_call_to_translate(self, node) -> bool:
        """Check if a node is a call to _() or get_translation()."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("_", "get_translation"):
                return True
        return False

    def visit_Assign(self, node: ast.Assign):
        if self._in_translation_call:
            self.generic_visit(node)
            return
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in USER_FACING_VAR_NAMES:
                s = _extract_string_value(node.value)
                if s:
                    self._add(node.lineno, s, f"var '{target.id}'")
        self.generic_visit(node)


def detect_file(filepath: Path, project_root: Path) -> List[Dict[str, Any]]:
    """Detect hardcoded strings in a single Python file."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    detector = StringDetector(filepath, project_root)
    detector._source_lines = source.split("\n")
    detector.visit(tree)
    return detector.findings


def detect_all(project_root: Path, targets: Optional[List[str]] = None) -> Dict[str, Any]:
    """Scan the project for hardcoded user-facing strings.

    Returns a report dict with findings grouped by file.
    """
    root = Path(project_root)
    scan_dirs = [root]
    if targets:
        scan_dirs = [root / t for t in targets]

    all_findings = []
    files_scanned = 0

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            if any(p in py_file.parts for p in SKIP_DIRS):
                continue
            findings = detect_file(py_file, root)
            all_findings.extend(findings)
            files_scanned += 1

    by_file = {}
    for f in all_findings:
        fpath = f["file"]
        if fpath not in by_file:
            by_file[fpath] = []
        by_file[fpath].append(f)

    return {
        "files_scanned": files_scanned,
        "total_findings": len(all_findings),
        "files_with_findings": len(by_file),
        "findings": by_file,
    }


def format_report(report: Dict[str, Any]) -> str:
    """Format detection report for terminal output."""
    lines = []
    lines.append(f"Scanned {report['files_scanned']} files, "
                 f"found {report['total_findings']} potential hardcoded strings "
                 f"in {report['files_with_findings']} files.\n")

    for fpath, findings in sorted(report["findings"].items()):
        lines.append(f"\n  {fpath} ({len(findings)} findings)")
        for f in findings[:20]:
            s = f["string"][:80]
            lines.append(f"    L{f['line']:4d} [{f['context']}] \"{s}\"")
        if len(findings) > 20:
            lines.append(f"    ... and {len(findings) - 20} more")

    return "\n".join(lines)
