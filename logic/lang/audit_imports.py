"""Cross-tool import quality checker.

Statically analyzes Python source code to enforce:
1. Cross-tool imports MUST go through logic/interface/main.py
2. CDMCP access MUST use logic/cdmcp_loader (not hardcoded paths)
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


_RAW_CDP_TAB_OPS = frozenset({"find_tab", "open_tab", "list_tabs"})

_CDMCP_HARDCODE_PATTERNS = (
    "_CDMCP_TOOL_DIR",
    "_OVERLAY_PATH",
    "_SESSION_MGR_PATH",
    "_INTERACT_PATH",
)


class ImportAuditor(ast.NodeVisitor):
    """AST visitor that collects import quality issues for a single file."""

    def __init__(self, filepath: Path, tool_name: str, project_root: Path):
        self.filepath = filepath
        self.tool_name = tool_name
        self.project_root = project_root
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

        # Rule IMP001: Cross-tool internal import (not through interface)
        if mod.startswith("tool.") and ".logic." in mod:
            parts = mod.split(".")
            other_tool = parts[1]
            if other_tool != self.tool_name:
                if "interface" not in mod:
                    self._add(node.lineno, Severity.ERROR, "IMP001",
                              f"Cross-tool internal import: 'from {mod}' — "
                              f"must import from tool.{other_tool}.logic.interface.main")
                else:
                    pass  # Good: uses interface

        # Rule IMP002: Raw CDP tab ops (should use CDMCP session.require_tab)
        if mod == "logic.chrome.session":
            bad = _RAW_CDP_TAB_OPS.intersection(names)
            if bad:
                self._add(node.lineno, Severity.ERROR, "IMP002",
                          f"Raw CDP tab operations imported: {sorted(bad)} — "
                          f"use CDMCP session.require_tab() for tab management")

        # Rule IMP003: Not using cdmcp_loader for CDMCP access
        # (detected by absence; we check in finalize)

        # Rule IMP004: ToolBase vs MCPToolBase (only for tools that use CDP/CDMCP)
        if mod == "logic.tool.blueprint.base" and "ToolBase" in names:
            self._uses_toolbase = True

        self.generic_visit(node)

    def check_source_lines(self, source: str):
        """Scan raw source for patterns not easily detected via AST."""
        self._source_lines = source.split("\n")
        has_cdmcp_loader = "cdmcp_loader" in source
        uses_cdmcp = False
        has_chrome_dep = ("logic.chrome" in source or "cdmcp" in source.lower()
                          or "CDPSession" in source or "find_tab" in source)

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()

            # Rule IMP003: Hardcoded CDMCP tool paths
            for pattern in _CDMCP_HARDCODE_PATTERNS:
                if pattern in stripped and "=" in stripped and "#" not in stripped[:stripped.index(pattern)]:
                    if "CDMCP" in stripped:
                        uses_cdmcp = True
                        self._add(i, Severity.ERROR, "IMP003",
                                  f"Hardcoded CDMCP path: '{stripped[:80]}' — "
                                  f"use 'from logic.cdmcp_loader import ...' instead")

            # Rule IMP003b: spec_from_file_location pointing to CDMCP
            if "spec_from_file_location" in stripped and "CDMCP" in stripped:
                uses_cdmcp = True
                self._add(i, Severity.ERROR, "IMP003",
                          "spec_from_file_location to CDMCP — use cdmcp_loader")

        if uses_cdmcp and not has_cdmcp_loader:
            self._add(1, Severity.WARNING, "IMP003",
                      "File uses CDMCP but does not import from cdmcp_loader")

        if getattr(self, "_uses_toolbase", False) and has_chrome_dep:
            self._add(1, Severity.WARNING, "IMP004",
                      "Uses ToolBase with Chrome/CDP — MCP-enabled tools should "
                      "use MCPToolBase from logic.tool.blueprint.mcp")


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

        visitor = ImportAuditor(py_file, tool_name, project_root)
        visitor.visit(tree)
        visitor.check_source_lines(source)
        issues.extend(visitor.issues)

    return issues


def audit_all_tools(project_root: Path,
                    exclude: Optional[List[str]] = None) -> Dict[str, List[ImportIssue]]:
    """Audit all tools under project_root/tool/."""
    tool_base = project_root / "tool"
    exclude = set(exclude or [])
    results: Dict[str, List[ImportIssue]] = {}

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
        lines.append("  IMP001: Cross-tool imports → use tool.X.logic.interface.main")
        lines.append("  IMP002: Raw CDP tab ops → use CDMCP session.require_tab()")
        lines.append("  IMP003: Hardcoded CDMCP paths → use logic.cdmcp_loader")
        lines.append("  IMP004: ToolBase → MCPToolBase for MCP tools")

    return "\n".join(lines)


def to_json(results: Dict[str, List[ImportIssue]]) -> str:
    """Export audit results as JSON."""
    out = {}
    for tool_name, issues in results.items():
        out[tool_name] = [i.to_dict() for i in issues]
    return json.dumps(out, indent=2, ensure_ascii=False)
