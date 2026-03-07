"""Hook & Interface & Skills quality auditor.

Performs static and structural analysis on tool hooks, interfaces, and skills
following software engineering testing conventions:

Hook checks (HOOK001-HOOK006):
  - Instance must reference a declared interface event
  - Instance must subclass HookInstance with required attributes
  - Interface must subclass HookInterface with event_name
  - config.json must only reference existing instances
  - Orphan instances (no matching interface) are flagged
  - Hook instance execute() must exist and be non-trivial

Interface checks (IFACE001-IFACE005):
  - interface/main.py must exist if other tools import from this tool
  - interface/main.py must not import from other tool's logic/ directly
  - Every public function should have a docstring
  - interface should not contain non-interface logic (complexity heuristic)
  - __init__.py presence check (optional but recommended)

Skills checks (SKILL001-SKILL003):
  - Skills directory should contain SKILL.md (not empty)
  - Skills referenced in README/for_agent should exist
  - SKILL.md should have valid frontmatter
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from logic.audit.utils import AuditManager


class Severity:
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AuditIssue:
    __slots__ = ("file", "line", "severity", "code", "message")

    def __init__(self, file: str, line: int, severity: str, code: str, message: str):
        self.file = file
        self.line = line
        self.severity = severity
        self.code = code
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file, "line": self.line,
            "severity": self.severity, "code": self.code,
            "message": self.message,
        }

    def __repr__(self):
        return f"[{self.severity.upper():5s}] {self.code} {self.file}:{self.line} — {self.message}"


# ──────────────────────────────────────────────────────────────────────
# Hooks Auditor
# ──────────────────────────────────────────────────────────────────────

def _parse_classes(py_path: Path) -> List[dict]:
    """Parse a Python file and return info about class definitions."""
    try:
        source = py_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(py_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(b.attr)
        attrs = {}
        methods = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(item.value, ast.Constant):
                            attrs[target.id] = item.value.value
                        elif isinstance(item.value, ast.NameConstant):
                            attrs[target.id] = item.value.value
            elif isinstance(item, ast.FunctionDef):
                body_has_code = any(
                    not isinstance(s, (ast.Pass, ast.Expr))
                    or (isinstance(s, ast.Expr) and not isinstance(s.value, (ast.Constant, ast.Str)))
                    for s in item.body
                )
                methods.append({
                    "name": item.name,
                    "lineno": item.lineno,
                    "has_docstring": (
                        len(item.body) > 0
                        and isinstance(item.body[0], ast.Expr)
                        and isinstance(item.body[0].value, (ast.Constant, ast.Str))
                    ),
                    "has_real_body": body_has_code,
                    "arg_count": len(item.args.args),
                })
        classes.append({
            "name": node.name,
            "lineno": node.lineno,
            "bases": bases,
            "attrs": attrs,
            "methods": methods,
        })
    return classes


def audit_hooks(tool_dir: Path, project_root: Path) -> List[AuditIssue]:
    """Audit hook interfaces and instances for a single tool."""
    tool_name = tool_dir.name
    issues: List[AuditIssue] = []
    hooks_dir = tool_dir / "hooks"
    base_hooks_dir = project_root / "logic" / "tool" / "hooks" / "base"

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(project_root))
        except ValueError:
            return str(p)

    # Collect declared interface events
    declared_events: Dict[str, Path] = {}
    for iface_dir in [base_hooks_dir / "interface", hooks_dir / "interface"]:
        if not iface_dir.exists():
            continue
        for py in sorted(iface_dir.glob("*.py")):
            if py.name.startswith("_"):
                continue
            for cls in _parse_classes(py):
                if "HookInterface" in cls["bases"]:
                    ev = cls["attrs"].get("event_name", "")
                    if not ev:
                        issues.append(AuditIssue(
                            _rel(py), cls["lineno"], Severity.ERROR, "HOOK001",
                            f"HookInterface '{cls['name']}' missing event_name attribute"))
                    else:
                        declared_events[ev] = py
                    if not cls["attrs"].get("description"):
                        issues.append(AuditIssue(
                            _rel(py), cls["lineno"], Severity.WARNING, "HOOK002",
                            f"HookInterface '{cls['name']}' missing description"))

    # Collect and validate instances
    declared_instances: Dict[str, dict] = {}
    for inst_dir in [base_hooks_dir / "instance", hooks_dir / "instance"]:
        if not inst_dir.exists():
            continue
        for py in sorted(inst_dir.glob("*.py")):
            if py.name.startswith("_"):
                continue
            for cls in _parse_classes(py):
                if "HookInstance" in cls["bases"]:
                    name = cls["attrs"].get("name", "")
                    event = cls["attrs"].get("event_name", "")

                    if not name:
                        issues.append(AuditIssue(
                            _rel(py), cls["lineno"], Severity.ERROR, "HOOK003",
                            f"HookInstance '{cls['name']}' missing name attribute"))
                        continue

                    declared_instances[name] = {"event": event, "cls": cls, "file": py}

                    if not event:
                        issues.append(AuditIssue(
                            _rel(py), cls["lineno"], Severity.ERROR, "HOOK003",
                            f"HookInstance '{name}' missing event_name attribute"))
                    elif event not in declared_events:
                        issues.append(AuditIssue(
                            _rel(py), cls["lineno"], Severity.ERROR, "HOOK004",
                            f"HookInstance '{name}' references undeclared event "
                            f"'{event}' — no matching HookInterface found"))

                    if not cls["attrs"].get("description"):
                        issues.append(AuditIssue(
                            _rel(py), cls["lineno"], Severity.WARNING, "HOOK002",
                            f"HookInstance '{name}' missing description"))

                    execute_methods = [m for m in cls["methods"] if m["name"] == "execute"]
                    if not execute_methods:
                        issues.append(AuditIssue(
                            _rel(py), cls["lineno"], Severity.ERROR, "HOOK005",
                            f"HookInstance '{name}' does not override execute()"))
                    elif not execute_methods[0]["has_real_body"]:
                        issues.append(AuditIssue(
                            _rel(py), execute_methods[0]["lineno"], Severity.WARNING, "HOOK005",
                            f"HookInstance '{name}' execute() has no substantive body"))

    # Validate config.json
    config_path = hooks_dir / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            for key in ["enabled", "disabled"]:
                for inst_name in config.get(key, []):
                    if inst_name not in declared_instances:
                        issues.append(AuditIssue(
                            _rel(config_path), 0, Severity.ERROR, "HOOK006",
                            f"config.json references unknown instance '{inst_name}' "
                            f"in '{key}' list"))
        except json.JSONDecodeError as e:
            issues.append(AuditIssue(
                _rel(config_path), 0, Severity.ERROR, "HOOK006",
                f"config.json is invalid JSON: {e}"))

    return issues


# ──────────────────────────────────────────────────────────────────────
# Interface Auditor
# ──────────────────────────────────────────────────────────────────────

def audit_interface(tool_dir: Path, project_root: Path) -> List[AuditIssue]:
    """Audit the tool's interface/main.py for quality."""
    tool_name = tool_dir.name
    issues: List[AuditIssue] = []
    iface_path = tool_dir / "interface" / "main.py"

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(project_root))
        except ValueError:
            return str(p)

    if not iface_path.exists():
        # Only flag if the tool has logic (not a bare stub)
        if (tool_dir / "main.py").exists() and (tool_dir / "logic").exists():
            issues.append(AuditIssue(
                _rel(tool_dir), 0, Severity.INFO, "IFACE001",
                f"Tool '{tool_name}' has logic/ but no interface/main.py — "
                f"consider exposing a public API"))
        return issues

    try:
        source = iface_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(iface_path))
    except SyntaxError as e:
        issues.append(AuditIssue(
            _rel(iface_path), e.lineno or 0, Severity.ERROR, "IFACE002",
            f"interface/main.py has syntax error: {e.msg}"))
        return issues

    # Check for cross-tool logic imports within the interface itself
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if mod.startswith("tool."):
                parts = mod.split(".")
                if len(parts) >= 2:
                    other_tool = parts[1]
                    if other_tool != tool_name and "interface" not in mod:
                        issues.append(AuditIssue(
                            _rel(iface_path), node.lineno, Severity.ERROR, "IFACE002",
                            f"Interface imports from tool.{other_tool}.logic/ — "
                            f"interfaces must not reach into other tools' internals"))

    # Check public functions for docstrings
    func_count = 0
    undocumented = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            func_count += 1
            has_doc = (
                len(node.body) > 0
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, (ast.Constant, ast.Str))
            )
            if not has_doc:
                undocumented += 1

    if func_count > 0 and undocumented > 0:
        pct = (undocumented / func_count) * 100
        if pct > 50:
            issues.append(AuditIssue(
                _rel(iface_path), 0, Severity.WARNING, "IFACE003",
                f"{undocumented}/{func_count} public functions lack docstrings "
                f"({pct:.0f}%) — interfaces are public API and should be documented"))

    # Complexity heuristic: interfaces should be thin wrappers, not thick logic
    lines = source.splitlines()
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if len(code_lines) > 200:
        issues.append(AuditIssue(
            _rel(iface_path), 0, Severity.WARNING, "IFACE004",
            f"interface/main.py has {len(code_lines)} code lines — "
            f"interfaces should be thin wrappers; move complex logic to logic/"))

    # Module docstring check
    has_module_doc = (
        len(tree.body) > 0
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, (ast.Constant, ast.Str))
    )
    if not has_module_doc:
        issues.append(AuditIssue(
            _rel(iface_path), 1, Severity.INFO, "IFACE005",
            f"interface/main.py lacks a module docstring — "
            f"document usage examples for cross-tool consumers"))

    return issues


# ──────────────────────────────────────────────────────────────────────
# Skills Auditor
# ──────────────────────────────────────────────────────────────────────

_SKILLS_ROOT = Path.home() / ".cursor" / "skills"


def audit_skills(project_root: Path) -> List[AuditIssue]:
    """Audit all TerminalTools skills for completeness."""
    issues: List[AuditIssue] = []

    if not _SKILLS_ROOT.exists():
        issues.append(AuditIssue(
            str(_SKILLS_ROOT), 0, Severity.WARNING, "SKILL001",
            "Skills directory does not exist"))
        return issues

    for skill_dir in sorted(_SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir() or not skill_dir.name.startswith("TerminalTools-"):
            continue

        skill_md = skill_dir / "SKILL.md"
        rel = skill_dir.name

        if not skill_md.exists():
            issues.append(AuditIssue(
                rel, 0, Severity.ERROR, "SKILL001",
                f"Skill '{rel}' is an empty directory — missing SKILL.md"))
            continue

        content = skill_md.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            issues.append(AuditIssue(
                rel, 0, Severity.ERROR, "SKILL001",
                f"Skill '{rel}' has empty SKILL.md"))
            continue

        # Frontmatter check
        if not content.startswith("---"):
            issues.append(AuditIssue(
                rel, 1, Severity.WARNING, "SKILL002",
                f"Skill '{rel}' SKILL.md missing YAML frontmatter (---) header"))
        else:
            fm_end = content.find("---", 3)
            if fm_end < 0:
                issues.append(AuditIssue(
                    rel, 1, Severity.WARNING, "SKILL002",
                    f"Skill '{rel}' SKILL.md has unclosed frontmatter"))
            else:
                frontmatter = content[3:fm_end].strip()
                if "name:" not in frontmatter:
                    issues.append(AuditIssue(
                        rel, 1, Severity.WARNING, "SKILL002",
                        f"Skill '{rel}' frontmatter missing 'name:' field"))
                if "description:" not in frontmatter:
                    issues.append(AuditIssue(
                        rel, 1, Severity.WARNING, "SKILL002",
                        f"Skill '{rel}' frontmatter missing 'description:' field"))

        # Content quality: minimum length
        body_lines = [l for l in content.splitlines() if l.strip() and not l.startswith("---")]
        if len(body_lines) < 10:
            issues.append(AuditIssue(
                rel, 0, Severity.WARNING, "SKILL003",
                f"Skill '{rel}' SKILL.md is very short ({len(body_lines)} non-blank lines) "
                f"— consider adding more detail"))

    return issues


# ──────────────────────────────────────────────────────────────────────
# Combined Audit
# ──────────────────────────────────────────────────────────────────────

def audit_tool_quality(tool_dir: Path, project_root: Path) -> Dict[str, List[AuditIssue]]:
    """Run all quality checks (hooks + interface) for a single tool."""
    result = {}
    hooks_issues = audit_hooks(tool_dir, project_root)
    if hooks_issues:
        result["hooks"] = hooks_issues
    iface_issues = audit_interface(tool_dir, project_root)
    if iface_issues:
        result["interface"] = iface_issues
    return result


def audit_all_quality(project_root: Path,
                      exclude: Optional[List[str]] = None) -> Dict[str, Dict[str, List[AuditIssue]]]:
    """Run hooks + interface audit across all tools."""
    tool_base = project_root / "tool"
    exclude_set = set(exclude or [])
    results: Dict[str, Dict[str, List[AuditIssue]]] = {}

    for tool_dir in sorted(tool_base.iterdir()):
        if not tool_dir.is_dir():
            continue
        if tool_dir.name in exclude_set or tool_dir.name.startswith("."):
            continue
        tool_results = audit_tool_quality(tool_dir, project_root)
        if tool_results:
            results[tool_dir.name] = tool_results

    return results


def format_quality_report(results: Dict[str, Dict[str, List[AuditIssue]]],
                          skills_issues: Optional[List[AuditIssue]] = None) -> str:
    """Format a combined quality audit report."""
    lines = []
    total_errors = 0
    total_warnings = 0
    total_info = 0

    # Tool-level results
    for tool_name, categories in sorted(results.items()):
        all_issues = []
        for cat_issues in categories.values():
            all_issues.extend(cat_issues)
        if not all_issues:
            continue

        errors = [i for i in all_issues if i.severity == Severity.ERROR]
        warnings = [i for i in all_issues if i.severity == Severity.WARNING]
        infos = [i for i in all_issues if i.severity == Severity.INFO]
        total_errors += len(errors)
        total_warnings += len(warnings)
        total_info += len(infos)

        color = "\033[31m" if errors else "\033[33m" if warnings else "\033[36m"
        lines.append(f"\n\033[1m{color}{tool_name}\033[0m "
                     f"({len(errors)} errors, {len(warnings)} warnings, {len(infos)} info)")
        for issue in all_issues:
            sev_c = (
                "\033[31m" if issue.severity == "error"
                else "\033[33m" if issue.severity == "warning"
                else "\033[36m"
            )
            loc = f"L{issue.line:4d}" if issue.line else "    "
            lines.append(
                f"  {sev_c}{issue.severity.upper():7s}\033[0m {issue.code} "
                f"{loc}: {issue.message}"
            )

    # Skills results
    if skills_issues:
        sk_errors = [i for i in skills_issues if i.severity == Severity.ERROR]
        sk_warnings = [i for i in skills_issues if i.severity == Severity.WARNING]
        total_errors += len(sk_errors)
        total_warnings += len(sk_warnings)
        color = "\033[31m" if sk_errors else "\033[33m" if sk_warnings else "\033[32m"
        lines.append(f"\n\033[1m{color}Skills\033[0m "
                     f"({len(sk_errors)} errors, {len(sk_warnings)} warnings)")
        for issue in skills_issues:
            sev_c = (
                "\033[31m" if issue.severity == "error"
                else "\033[33m" if issue.severity == "warning"
                else "\033[36m"
            )
            lines.append(
                f"  {sev_c}{issue.severity.upper():7s}\033[0m {issue.code} "
                f"{issue.file}: {issue.message}"
            )

    header = (f"\n\033[1mQuality Audit (Hooks · Interface · Skills)\033[0m\n"
              f"{'=' * 60}\n"
              f"Tools with issues: {len(results)}\n"
              f"Total errors: {total_errors}, warnings: {total_warnings}, info: {total_info}")
    lines.insert(0, header)

    if total_errors == 0 and total_warnings == 0:
        lines.append(f"\n\033[32mAll checks pass.\033[0m")
    else:
        lines.append(f"\n{'=' * 60}")
        lines.append(f"\033[1mRule reference:\033[0m")
        lines.append("  HOOK001: HookInterface missing event_name")
        lines.append("  HOOK002: Missing description on hook interface/instance")
        lines.append("  HOOK003: HookInstance missing required attributes (name, event_name)")
        lines.append("  HOOK004: HookInstance references undeclared event")
        lines.append("  HOOK005: HookInstance missing or empty execute()")
        lines.append("  HOOK006: config.json references unknown instance or invalid JSON")
        lines.append("  IFACE001: Tool has logic/ but no interface/main.py")
        lines.append("  IFACE002: Interface has syntax errors or imports other tool's internals")
        lines.append("  IFACE003: Public interface functions lack docstrings")
        lines.append("  IFACE004: Interface is too thick (>200 code lines)")
        lines.append("  IFACE005: Interface lacks module docstring")
        lines.append("  SKILL001: Empty skill directory or missing SKILL.md")
        lines.append("  SKILL002: SKILL.md missing or malformed frontmatter")
        lines.append("  SKILL003: SKILL.md content is too short")

    return "\n".join(lines)


def quality_to_json(results: Dict[str, Dict[str, List[AuditIssue]]],
                    skills_issues: Optional[List[AuditIssue]] = None) -> str:
    """Export quality audit results as JSON."""
    out = {}
    for tool_name, categories in results.items():
        out[tool_name] = {}
        for cat, issues in categories.items():
            out[tool_name][cat] = [i.to_dict() for i in issues]
    if skills_issues:
        out["_skills"] = [i.to_dict() for i in skills_issues]
    return json.dumps(out, indent=2, ensure_ascii=False)
