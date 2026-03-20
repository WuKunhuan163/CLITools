"""Argparse three-tier conformance audit.

Scans tool main.py files for argparse argument definitions and checks
whether they follow the dash-level indicator convention:

- ---<name>  = Tier 1: shared eco commands (implementation in logic/_/)
- --<name>   = Tier 2: hierarchical tool-specific commands
- -<name>    = Tier 3: decorator/modifier flags

Violations:
- Using -- for a known eco command name (should be ---)
- Using -- for a known decorator name (should be -)
- Using --- for a non-registered eco command
"""
import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple


SHARED_ECO_COMMANDS = {
    "dev", "test", "setup", "config", "eco", "skills",
    "hooks", "audit", "assistant", "agent", "ask", "plan",
    "endpoint", "install", "uninstall", "rule",
    "call-register",
}

DECORATOR_FLAGS = {
    "no-warning", "tool-quiet",
}

ALL_RESERVED = SHARED_ECO_COMMANDS | DECORATOR_FLAGS


def find_argparse_options(filepath: Path) -> List[Tuple[int, str, str]]:
    """Extract argparse add_argument calls and their option strings.
    
    Returns list of (line_number, option_string, raw_line).
    """
    results = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return results
    
    pattern = re.compile(
        r'add_argument\s*\(\s*["\'](-{1,3}[\w-]+)["\']',
        re.MULTILINE,
    )
    
    for i, line in enumerate(text.split("\n"), 1):
        for m in pattern.finditer(line):
            results.append((i, m.group(1), line.strip()))
    
    return results


def audit_file(filepath: Path, is_base: bool = False) -> List[Dict]:
    """Audit a single file for argparse convention violations.
    
    Args:
        is_base: If True, this is the base tool / shared infrastructure.
                 eco_command_wrong_prefix only applies to base/shared code,
                 NOT to individual tools (--<name> is valid Tier 2 in tools).
    """
    findings = []
    options = find_argparse_options(filepath)
    
    for line_num, opt_str, raw_line in options:
        name = opt_str.lstrip("-")
        dash_count = len(opt_str) - len(name)
        
        if name in SHARED_ECO_COMMANDS and dash_count == 2 and is_base:
            findings.append({
                "file": str(filepath),
                "line": line_num,
                "option": opt_str,
                "violation": "eco_command_wrong_prefix",
                "message": f"'{opt_str}' is a shared eco command — should use '---{name}' (triple dash)",
                "severity": "warning",
            })
        
        if name in DECORATOR_FLAGS and dash_count == 2:
            findings.append({
                "file": str(filepath),
                "line": line_num,
                "option": opt_str,
                "violation": "decorator_wrong_prefix",
                "message": f"'{opt_str}' is a decorator — should use '-{name}' (single dash)",
                "severity": "warning",
            })
        
        if dash_count == 3 and name not in SHARED_ECO_COMMANDS:
            findings.append({
                "file": str(filepath),
                "line": line_num,
                "option": opt_str,
                "violation": "unregistered_eco_command",
                "message": f"'{opt_str}' uses triple-dash but '{name}' is not a registered eco command",
                "severity": "error",
            })
    
    return findings


def audit_project(root: Path) -> Dict:
    """Run the argparse audit across the entire project."""
    all_findings = []
    files_scanned = 0
    
    base_py = root / "logic" / "tool" / "blueprint" / "base.py"
    shared_infra = root / "logic" / "_"
    
    # Scan tool main.py files (Tier 2 — tool-specific parsers)
    tool_dir = root / "tool"
    if tool_dir.exists():
        for main_py in tool_dir.rglob("main.py"):
            files_scanned += 1
            findings = audit_file(main_py, is_base=False)
            all_findings.extend(findings)
    
    # Scan logic/ for argparse usage
    logic_dir = root / "logic"
    if logic_dir.exists():
        for py_file in logic_dir.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            files_scanned += 1
            is_base = (
                (py_file == base_py or shared_infra in py_file.parents)
                and "archived" not in py_file.parts
            )
            findings = audit_file(py_file, is_base=is_base)
            all_findings.extend(findings)
    
    # Scan base tool dispatch patterns
    if base_py.exists():
        base_findings = audit_base_tool(base_py)
        all_findings.extend(base_findings)
    
    errors = [f for f in all_findings if f["severity"] == "error"]
    warnings = [f for f in all_findings if f["severity"] == "warning"]
    
    return {
        "files_scanned": files_scanned,
        "total_findings": len(all_findings),
        "errors": len(errors),
        "warnings": len(warnings),
        "findings": all_findings,
    }


def audit_base_tool(base_py: Path) -> List[Dict]:
    """Specifically audit base.py for eco command dispatch patterns.
    
    Checks that _extract_flag_args() calls use the correct prefix.
    """
    findings = []
    try:
        text = base_py.read_text(encoding="utf-8")
    except Exception:
        return findings
    
    pattern = re.compile(
        r'_extract_flag_args\s*\(\s*"(-{1,3}[\w-]+)"\s*\)',
    )
    
    for i, line in enumerate(text.split("\n"), 1):
        for m in pattern.finditer(line):
            opt_str = m.group(1)
            name = opt_str.lstrip("-")
            dash_count = len(opt_str) - len(name)
            
            if name in SHARED_ECO_COMMANDS and dash_count != 3:
                findings.append({
                    "file": str(base_py),
                    "line": i,
                    "option": opt_str,
                    "violation": "base_eco_wrong_prefix",
                    "message": f"base.py dispatches eco command '{opt_str}' — should use '---{name}'",
                    "severity": "warning",
                })
    
    return findings


def print_report(result: Dict):
    """Print human-readable audit report."""
    BOLD = "\033[1m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    
    print(f"\n{BOLD}Argparse Three-Tier Conformance Audit{RESET}")
    print(f"  Scanned {result['files_scanned']} files")
    print(f"  Found {result['total_findings']} issues "
          f"({RED}{result['errors']} errors{RESET}, "
          f"{YELLOW}{result['warnings']} warnings{RESET})")
    
    if not result["findings"]:
        print(f"\n  {GREEN}{BOLD}All clear.{RESET} All argparse options follow the three-tier convention.")
        return
    
    by_violation = {}
    for f in result["findings"]:
        key = f["violation"]
        by_violation.setdefault(key, []).append(f)
    
    for violation_type, findings in sorted(by_violation.items()):
        color = RED if findings[0]["severity"] == "error" else YELLOW
        print(f"\n  {color}{BOLD}{violation_type}{RESET} ({len(findings)} issues)")
        
        for f in findings[:10]:
            rel_path = f["file"].split("AITerminalTools/")[-1] if "AITerminalTools/" in f["file"] else f["file"]
            print(f"    L{f['line']:4d} {DIM}{rel_path}{RESET}")
            print(f"          {f['message']}")
        
        if len(findings) > 10:
            print(f"    {DIM}... and {len(findings) - 10} more{RESET}")


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parent.parent.parent.parent
    result = audit_project(root)
    print_report(result)
    sys.exit(1 if result["errors"] > 0 else 0)
