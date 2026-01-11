#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

# Use resolve() to get the actual location of the script
current_dir = Path(__file__).resolve().parent
# project_root is two levels up: tool/OVERLEAF -> tool -> root
project_root = current_dir.parent.parent

# Add the directory containing 'proj' to sys.path
sys.path.append(str(current_dir))
if project_root.exists():
    sys.path.append(str(project_root))

# Localization and Color setup
try:
    from proj.language_utils import get_translation
    from proj.config import get_colors
except ImportError:
    def get_translation(d, k, default): return default
    def get_colors(): return {"RESET": "\033[0m", "GREEN": "\033[32m", "BLUE": "\033[34m", "YELLOW": "\033[33m", "RED": "\033[31m", "BOLD": "\033[1m"}

COLORS = get_colors()
RESET = COLORS.get("RESET", "\033[0m")
GREEN = COLORS.get("GREEN", "\033[32m")
BLUE = COLORS.get("BLUE", "\033[34m")
YELLOW = COLORS.get("YELLOW", "\033[33m")
RED = COLORS.get("RED", "\033[31m")
BOLD = COLORS.get("BOLD", "\033[1m")

TOOL_PROJ_DIR = current_dir / "proj"

def _(key, default, **kwargs):
    return get_translation(str(TOOL_PROJ_DIR), key, default).format(**kwargs)

def get_tex_path():
    """Check for portable TeX distribution in proj/installations."""
    # TinyTeX usually installs to ~/Library/TinyTeX on macOS
    # But we want to support a local version if possible
    local_tex = TOOL_PROJ_DIR / "installations" / "TinyTeX" / "bin" / "universal-darwin"
    if local_tex.exists():
        return str(local_tex)
    return None

def compile_latex(tex_file, output_dir=None, latex_options=None, no_shell_escape=False):
    """编译LaTeX文件"""
    tex_path = Path(tex_file).resolve()
    if not tex_path.exists():
        print(f"{RED}" + _("file_not_found", "Error: File not found: {file}", file=tex_file) + f"{RESET}")
        return 1
    
    filename = tex_path.stem
    print(_("compiling_start", "Starting LaTeX compilation for: {name}", name=tex_path.name))
    
    directory = tex_path.parent
    
    # Setup environment with portable TeX if available
    env = os.environ.copy()
    portable_tex = get_tex_path()
    if portable_tex:
        env["PATH"] = f"{portable_tex}:{env.get('PATH', '')}"
        print(_("using_portable_tex", "Using portable TeX from {path}", path=portable_tex))

    # Build command
    all_options = ['-interaction=nonstopmode']
    if not no_shell_escape:
        all_options.append('-shell-escape')
    if latex_options:
        all_options.extend(latex_options)
    
    pdflatex_cmd = 'pdflatex ' + ' '.join(all_options)
    cmd = ['latexmk', '-pdf', f'-pdflatex={pdflatex_cmd}', f'{filename}.tex']
    
    try:
        result = subprocess.run(cmd, cwd=str(directory), env=env, text=True)
        
        if result.returncode == 0:
            # Success
            pdf_file = directory / f"{filename}.pdf"
            if pdf_file.exists():
                final_pdf_path = pdf_file
                if output_dir:
                    output_path = Path(output_dir).resolve()
                    output_path.mkdir(parents=True, exist_ok=True)
                    final_pdf_path = output_path / f"{filename}.pdf"
                    shutil.move(str(pdf_file), str(final_pdf_path))
                
                print(f"{GREEN}{BOLD}" + _("compile_success", "LaTeX compilation successful!") + f"{RESET}")
                print(_("generated_pdf", "Generated PDF: {path}", path=final_pdf_path))
                return 0
            else:
                print(f"{RED}" + _("pdf_not_generated", "Error: PDF not generated.") + f"{RESET}")
                return 1
        else:
            print(f"{RED}" + _("compile_failed", "Error: LaTeX compilation failed! (Exit code: {code})", code=result.returncode) + f"{RESET}")
            return result.returncode
            
    except Exception as e:
        print(f"{RED}" + _("compilation_error", "Error during compilation: {error}", error=e) + f"{RESET}")
        return 1

def list_templates():
    templates_dir = TOOL_PROJ_DIR / "templates"
    if not templates_dir.exists():
        return []
    return [d.name for d in templates_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

def copy_template(template_name, target_dir):
    templates_dir = TOOL_PROJ_DIR / "templates"
    template_path = templates_dir / template_name
    target_path = Path(target_dir).resolve()
    
    if not template_path.exists():
        print(f"{RED}" + _("template_not_found", "Template '{name}' not found.", name=template_name) + f"{RESET}")
        return 1
    
    target_path.mkdir(parents=True, exist_ok=True)
    for item in template_path.iterdir():
        if item.name.startswith('.'): continue
        target_item = target_path / item.name
        if item.is_dir():
            shutil.copytree(item, target_item, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target_item)
            
    print(f"{GREEN}{BOLD}" + _("template_success", "Template '{name}' copied successfully to '{path}'", name=template_name, path=target_path) + f"{RESET}")
    return 0

def main():
    import argparse
    parser = argparse.ArgumentParser(description=_("overleaf_description", 'OVERLEAF - Local LaTeX compilation and template management'))
    parser.add_argument('tex_file', nargs='?', help=_("tex_file_help", 'Path to LaTeX file'))
    parser.add_argument('--output-dir', help=_("output_dir_help", 'Output directory for the generated PDF'))
    parser.add_argument('--template', nargs=2, metavar=('NAME', 'DIR'), help=_("template_help", 'Copy template to target directory'))
    parser.add_argument('--list-templates', action='store_true', help=_("list_templates_help", 'List all available templates'))
    parser.add_argument('--latex-options', action='append', default=[], help=_("latex_options_help", 'Extra options for pdflatex'))
    parser.add_argument('--no-shell-escape', action='store_true', help=_("no_shell_escape_help", 'Disable -shell-escape'))

    args = parser.parse_args()

    if args.list_templates:
        templates = list_templates()
        if templates:
            print(_("available_templates", "Available templates:"))
            for t in templates:
                print(f"  - {t}")
        else:
            print(_("no_templates", "No templates found."))
        return 0

    if args.template:
        return copy_template(args.template[0], args.template[1])

    tex_file = args.tex_file
    if not tex_file:
        # Try to use USERINPUT to get the file path instead of direct tkinter
        # But for now let's just use the argparse argument or print help
        parser.print_help()
        return 1

    return compile_latex(tex_file, args.output_dir, args.latex_options, args.no_shell_escape)

if __name__ == "__main__":
    sys.exit(main())
