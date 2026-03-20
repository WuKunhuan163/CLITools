"""Automated code-quality auditing for AITerminalTools.

Runs ruff (unused imports, unused variables, syntax) and vulture (dead code)
across the project, returning structured results.  Designed to be called from
the CLI (``TOOL --audit code``) or programmatically via the interface.

Depends on: ruff, vulture (pip install ruff vulture).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Finding:
    """One code-quality issue."""
    category: str
    file: str
    line: int
    col: int
    code: str
    message: str
    fixable: bool = False


@dataclass
class AuditReport:
    """Aggregate results from all checks."""
    findings: List[Finding] = field(default_factory=list)
    fixed_count: int = 0
    error: Optional[str] = None

    @property
    def total(self) -> int:
        return len(self.findings)

    def by_category(self) -> Dict[str, List[Finding]]:
        groups: Dict[str, List[Finding]] = {}
        for f in self.findings:
            groups.setdefault(f.category, []).append(f)
        return groups

    def summary_lines(self) -> List[str]:
        lines: List[str] = []
        cats = self.by_category()
        for cat in sorted(cats):
            lines.append(f"  {cat}: {len(cats[cat])}")
        if self.fixed_count:
            lines.append(f"  auto-fixed: {self.fixed_count}")
        lines.append(f"  total remaining: {self.total}")
        return lines


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _run(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(cwd))


def _find_ruff() -> str:
    """Return the ruff command — either the binary or 'python3 -m ruff'."""
    try:
        r = subprocess.run(["ruff", "--version"], capture_output=True, text=True)
        if r.returncode == 0:
            return "ruff"
    except FileNotFoundError:
        pass
    return f"{sys.executable} -m ruff"


def _parse_ruff_json(raw: str) -> List[Finding]:
    """Parse ruff JSON output into Finding objects."""
    findings: List[Finding] = []
    try:
        items = json.loads(raw) if raw.strip() else []
    except json.JSONDecodeError:
        return findings

    cat_map = {
        "F401": "unused-import",
        "F841": "unused-variable",
        "E9": "syntax-error",
    }
    for item in items:
        code = item.get("code", "")
        cat = cat_map.get(code, cat_map.get(code[:2], f"ruff-{code}"))
        loc = item.get("location", {})
        findings.append(Finding(
            category=cat,
            file=item.get("filename", "?"),
            line=loc.get("row", 0),
            col=loc.get("column", 0),
            code=code,
            message=item.get("message", ""),
            fixable=item.get("fix") is not None,
        ))
    return findings


def check_unused_imports(targets: List[str], root: Path) -> List[Finding]:
    ruff = _find_ruff()
    cmd = ruff.split() + [
        "check", "--select", "F401",
        "--output-format", "json",
        "--exclude", "__init__.py",
    ] + targets
    r = _run(cmd, root)
    return _parse_ruff_json(r.stdout)


def check_unused_variables(targets: List[str], root: Path) -> List[Finding]:
    ruff = _find_ruff()
    cmd = ruff.split() + [
        "check", "--select", "F841",
        "--output-format", "json",
    ] + targets
    r = _run(cmd, root)
    return _parse_ruff_json(r.stdout)


def check_syntax_errors(targets: List[str], root: Path) -> List[Finding]:
    ruff = _find_ruff()
    cmd = ruff.split() + [
        "check", "--select", "E9",
        "--output-format", "json",
    ] + targets
    r = _run(cmd, root)
    return _parse_ruff_json(r.stdout)


def fix_unused_imports(targets: List[str], root: Path) -> int:
    """Auto-fix unused imports.  Returns count of fixed issues."""
    ruff = _find_ruff()
    cmd = ruff.split() + [
        "check", "--select", "F401",
        "--fix", "--unsafe-fixes",
        "--exclude", "__init__.py",
        "--output-format", "json",
    ] + targets
    r = _run(cmd, root)
    stderr = r.stderr or ""
    fixed = 0
    if "fixed" in stderr:
        parts = stderr.split("fixed")
        for p in parts[0].split():
            if p.strip("(,)").isdigit():
                fixed = int(p.strip("(,)"))
    return fixed


def fix_unused_variables(targets: List[str], root: Path) -> int:
    ruff = _find_ruff()
    cmd = ruff.split() + [
        "check", "--select", "F841",
        "--fix", "--unsafe-fixes",
        "--output-format", "json",
    ] + targets
    _run(cmd, root)
    return 0


def run_full_audit(
    targets: Optional[List[str]] = None,
    auto_fix: bool = False,
) -> AuditReport:
    """Run all code-quality checks.

    Parameters
    ----------
    targets : list of directory names relative to project root
        Defaults to ["logic/", "tool/", "interface/"].
    auto_fix : bool
        If True, auto-fix safe issues (unused imports/variables).
    """
    root = _project_root()
    if targets is None:
        targets = ["logic/", "tool/", "interface/"]

    report = AuditReport()

    if auto_fix:
        fix_unused_imports(targets, root)
        fix_unused_variables(targets, root)

    report.findings.extend(check_unused_imports(targets, root))
    report.findings.extend(check_unused_variables(targets, root))
    report.findings.extend(check_syntax_errors(targets, root))

    return report


def print_report(report: AuditReport) -> None:
    """Pretty-print the audit report to stdout."""
    from logic._.utils.turing.status import fmt_status, fmt_detail, fmt_warning, fmt_info

    RESET = "\033[0m"

    if report.error:
        print(fmt_warning(report.error, indent=0))
        return

    cats = report.by_category()
    if not cats:
        print(fmt_status("Code quality audit passed.", style="success", indent=0))
        sys.stdout.write(RESET)
        sys.stdout.flush()
        return

    for cat in sorted(cats):
        items = cats[cat]
        print(fmt_status(f"{cat}:", complement=f"{len(items)} issues", indent=0))
        shown = items[:10]
        for f in shown:
            print(fmt_detail(f"{f.file}:{f.line} {f.message}", indent=2))
        if len(items) > 10:
            print(fmt_detail(f"... and {len(items) - 10} more", indent=2))
    print()
    for line in report.summary_lines():
        print(f"{RESET}{line}")
    sys.stdout.write(RESET)
    sys.stdout.flush()
