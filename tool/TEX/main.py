#!/usr/bin/env python3
"""TEX — Report compilation tool.

Converts Markdown reports to PDF using markdown + weasyprint.
Future: full LaTeX support via tectonic or texlive.
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
while PROJECT_ROOT != PROJECT_ROOT.parent:
    if (PROJECT_ROOT / "tool.json").exists():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _get_colors():
    from logic._.config import get_color
    return {
        "BOLD": get_color("BOLD", "\033[1m"),
        "GREEN": get_color("GREEN", "\033[32m"),
        "RED": get_color("RED", "\033[31m"),
        "DIM": get_color("DIM", "\033[2m"),
        "RESET": get_color("RESET", "\033[0m"),
    }


def cmd_compile(args):
    """Compile Markdown to PDF."""
    c = _get_colors()
    if not args:
        print(f"  {c['RED']}Usage:{c['RESET']} TEX compile <file.md> [--output <dir>]")
        sys.exit(1)

    source = Path(args[0])
    if not source.exists():
        report_dir = PROJECT_ROOT / "report"
        candidate = report_dir / args[0]
        if candidate.exists():
            source = candidate

    if not source.exists():
        print(f"  {c['RED']}{c['BOLD']}Not found.{c['RESET']} {c['DIM']}{args[0]}{c['RESET']}")
        sys.exit(1)

    output_dir = PROJECT_ROOT / "report" / "pdf"
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_dir = Path(args[idx + 1])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / (source.stem + ".pdf")

    try:
        from tool.TEX.logic.compiler import compile_md_to_pdf
        compile_md_to_pdf(source, output_file)
        print(f"  {c['BOLD']}{c['GREEN']}Compiled.{c['RESET']} {c['DIM']}{output_file}{c['RESET']}")

    except ImportError as e:
        missing = str(e).split("'")[1] if "'" in str(e) else str(e)
        print(f"  {c['RED']}{c['BOLD']}Missing dependency.{c['RESET']} {c['DIM']}pip install {missing}{c['RESET']}")
        sys.exit(1)
    except Exception as e:
        print(f"  {c['RED']}{c['BOLD']}Compilation failed.{c['RESET']} {c['DIM']}{e}{c['RESET']}")
        sys.exit(1)


def cmd_list(args):
    """List reports."""
    from logic._.dev.report import list_reports
    c = _get_colors()
    scope = args[0] if args else "root"
    reports = list_reports(scope)
    if not reports:
        print(f"  {c['DIM']}No reports in scope '{scope}'.{c['RESET']}")
        return
    for r in reports:
        size_kb = r["size"] / 1024
        print(f"  {c['BOLD']}{r['name']}{c['RESET']} {c['DIM']}({size_kb:.1f}KB){c['RESET']}")


def cmd_template(_args):
    """Show report template."""
    c = _get_colors()
    template = """# Report Title

**Date**: {date}
**Author**: Agent
**Context**: What prompted this investigation

## Summary

Brief overview of findings.

## Findings

- Key finding 1
- Key finding 2

## Impact

What changed as a result.

## References

- Files: `path/to/relevant/file.py`
- Reports: `report/YYYY-MM-DD_related.md`
"""
    from datetime import date
    print(template.format(date=date.today().isoformat()))


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("TEX — Report compilation tool")
        print()
        print("Commands:")
        print("  compile <file.md>  Compile Markdown report to PDF")
        print("  list [scope]       List available reports")
        print("  template           Show report template")
        return

    cmd = args[0]
    rest = args[1:]

    commands = {
        "compile": cmd_compile,
        "list": cmd_list,
        "template": cmd_template,
    }

    if cmd in commands:
        commands[cmd](rest)
    else:
        print(f"Unknown command: {cmd}. Use 'TEX help' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
