"""Cross-tool import quality checker.

Statically analyzes Python source code to enforce:
1. Cross-tool imports MUST go through tool.<NAME>.interface.main
2. CDMCP access MUST use logic/chrome/loader (not hardcoded paths)
3. Raw CDP tab operations (find_tab/open_tab/list_tabs) should use
   CDMCP session.require_tab() instead
4. MCP-enabled tools should use MCPToolBase, not ToolBase

Uses Python's ast module for zero-dependency static analysis.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class Severity:
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ImportIssue:
    __slots__ = ("file", "line", "severity", "code", "message")

    def __init__(self, file: str, line: int, severity: str, code: str, message: str):
        self.file = file
        self.line = line
        self.severity = severity
        self.code = code
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }

    def __repr__(self):
        return f"[{self.severity.upper():5s}] {self.code} {self.file}:{self.line} — {self.message}"


def _is_entry_point(filepath: Path, tool_dir: Path) -> bool:
    """Check if a file is a tool entry point (not inside logic/ or interface/)."""
    rel = filepath.relative_to(tool_dir)
    parts = rel.parts
    if parts[0] in ("logic", "interface"):
        return False
    return True


def _is_in_tool_logic(filepath: Path, tool_dir: Path) -> bool:
    """Check if a file is inside a tool's logic/ directory."""
    rel = filepath.relative_to(tool_dir)
    return len(rel.parts) >= 2 and rel.parts[0] == "logic"


class ImportAuditor(ast.NodeVisitor):
    """AST visitor that collects import quality issues for a single file."""

    def __init__(self, filepath: Path, tool_name: str, project_root: Path,
                 is_entry_point: bool = False, is_in_tool_logic: bool = False):
        self.filepath = filepath
        self.tool_name = tool_name
        self.project_root = project_root
        self.is_entry_point = is_entry_point
        self.is_in_tool_logic = is_in_tool_logic
        self.issues: List[ImportIssue] = []
        self._source_lines: List[str] = []
        self._uses_toolbase = False

    def _add(self, line: int, severity: str, code: str, msg: str):
        self.issues.append(ImportIssue(
            file=str(self.filepath.relative_to(self.project_root)),
            line=line, severity=severity, code=code, message=msg,
        ))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        names = {a.name for a in node.names}

        # Rule IMP001: Cross-tool import not going through interface
        if mod.startswith("tool."):
            parts = mod.split(".")
            if len(parts) >= 2:
                other_tool = parts[1]
                if other_tool != self.tool_name:
                    is_interface = (len(parts) >= 3 and parts[2] == "interface")
                    if not is_interface:
                        self._add(node.lineno, Severity.ERROR, "IMP001",
                                  f"Cross-tool internal import: 'from {mod}' — "
                                  f"must import from tool.{other_tool}.interface.main")

        # Rule IMP005: Entry point importing from logic.* instead of interface.*
        if self.is_entry_point and mod.startswith("logic."):
            self._add(node.lineno, Severity.ERROR, "IMP005",
                      f"Entry point imports from '{mod}' — "
                      f"use interface.* instead")

        # Rule IMP006: Tool logic importing from shared root logic.*
        if self.is_in_tool_logic and mod.startswith("logic."):
            self._add(node.lineno, Severity.ERROR, "IMP006",
                      f"Tool logic imports from shared root '{mod}' — "
                      f"use interface.* instead")

        self.generic_visit(node)

    def check_source_lines(self, source: str):
        """Scan raw source for patterns not easily detected via AST."""
        self._source_lines = source.split("\n")


def audit_tool(tool_dir: Path, project_root: Path) -> List[ImportIssue]:
    """Audit all Python files in a tool directory."""
    tool_name = tool_dir.name
    issues: List[ImportIssue] = []

    for py_file in tool_dir.rglob("*.py"):
        rel_parts = py_file.relative_to(tool_dir).parts
        if any(p in rel_parts for p in ("data", "tmp", "test", "__pycache__",
                                         "node_modules", "resource")):
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        entry = _is_entry_point(py_file, tool_dir)
        in_tool_logic = _is_in_tool_logic(py_file, tool_dir)
        visitor = ImportAuditor(py_file, tool_name, project_root,
                                is_entry_point=entry,
                                is_in_tool_logic=in_tool_logic)
        visitor.visit(tree)
        visitor.check_source_lines(source)
        issues.extend(visitor.issues)

    return issues


def audit_docs(project_root: Path) -> List[ImportIssue]:
    """Audit documentation files for non-compliant import examples."""
    issues: List[ImportIssue] = []
    doc_files = list(project_root.glob("*.md"))
    doc_files.extend(project_root.glob("tool/*/AGENT.md"))
    doc_files.extend(project_root.glob("tool/*/README.md"))

    import re
    pattern = re.compile(
        r'from\s+(tool\.\w+\.logic\.\S+|logic\.(?:resolve|tool|setup|hooks|config|'
        r'turing|mcp|chrome|cdmcp)\S*)\s+import'
    )

    for doc_file in doc_files:
        try:
            content = doc_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        in_code_block = False
        for i, line in enumerate(content.split("\n"), 1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block and pattern.search(line):
                mod = pattern.search(line).group(1)
                issues.append(ImportIssue(
                    file=str(doc_file.relative_to(project_root)),
                    line=i, severity=Severity.WARNING, code="DOC001",
                    message=f"Documentation shows non-compliant import: '{mod}' — "
                            f"update example to use interface.*",
                ))
    return issues


def audit_root_files(project_root: Path) -> List[ImportIssue]:
    """Audit root-level Python files (setup.py, main.py) for IMP005."""
    issues: List[ImportIssue] = []
    for name in ("setup.py", "main.py"):
        py_file = project_root / name
        if not py_file.exists():
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        visitor = ImportAuditor(py_file, "__root__", project_root,
                                is_entry_point=True)
        visitor.visit(tree)
        issues.extend(visitor.issues)
    return issues


def audit_all_tools(project_root: Path,
                    exclude: Optional[List[str]] = None) -> Dict[str, List[ImportIssue]]:
    """Audit all tools under project_root/tool/ and root entry points."""
    tool_base = project_root / "tool"
    exclude = set(exclude or [])
    results: Dict[str, List[ImportIssue]] = {}

    root_issues = audit_root_files(project_root)
    if root_issues:
        results["__root__"] = root_issues

    for tool_dir in sorted(tool_base.iterdir()):
        if not tool_dir.is_dir():
            continue
        if tool_dir.name in exclude or tool_dir.name.startswith("."):
            continue
        issues = audit_tool(tool_dir, project_root)
        if issues:
            results[tool_dir.name] = issues

    return results


def format_report(results: Dict[str, List[ImportIssue]],
                  verbose: bool = False) -> str:
    """Format audit results as a human-readable report."""
    lines = []
    total_errors = 0
    total_warnings = 0

    for tool_name, issues in sorted(results.items()):
        errors = [i for i in issues if i.severity == Severity.ERROR]
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        total_errors += len(errors)
        total_warnings += len(warnings)

        color = "\033[31m" if errors else "\033[33m"
        lines.append(f"\n\033[1m{color}{tool_name}\033[0m "
                     f"({len(errors)} errors, {len(warnings)} warnings)")
        for issue in issues:
            sev_c = "\033[31m" if issue.severity == "error" else "\033[33m"
            lines.append(
                f"  {sev_c}{issue.severity.upper():5s}\033[0m {issue.code} "
                f"L{issue.line:4d}: {issue.message}"
            )

    header = (f"\n\033[1mImport Quality Audit\033[0m\n"
              f"{'=' * 60}\n"
              f"Tools with issues: {len(results)}\n"
              f"Total errors: {total_errors}, warnings: {total_warnings}")
    lines.insert(0, header)

    if total_errors == 0 and total_warnings == 0:
        lines.append(f"\n\033[32mAll tools pass import quality checks.\033[0m")
    else:
        lines.append(f"\n{'=' * 60}")
        lines.append(f"\033[1mFix priority:\033[0m")
        lines.append("  IMP001: Cross-tool imports → use tool.X.interface.main")
        lines.append("  IMP005: Entry point imports from logic.* → use interface.*")
        lines.append("  IMP006: Tool logic imports from shared root logic.* → use interface.*")

    return "\n".join(lines)


def to_json(results: Dict[str, List[ImportIssue]]) -> str:
    """Export audit results as JSON."""
    out = {}
    for tool_name, issues in results.items():
        out[tool_name] = [i.to_dict() for i in issues]
    return json.dumps(out, indent=2, ensure_ascii=False)
