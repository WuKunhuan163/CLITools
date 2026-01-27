#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEX Tool
- Local LaTeX compilation and template management.
- Replaces former OVERLEAF tool.
"""

import os
import sys
import argparse
import subprocess
import shutil
import hashlib
import random
import time
from pathlib import Path
from typing import List, Optional

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from logic.tool.base import ToolBase
    from logic.config import get_color
    from logic.utils import get_logic_dir
except ImportError:
    class ToolBase:
        def __init__(self, name):
            self.tool_name = name
            self.project_root = Path(__file__).resolve().parent.parent.parent
            self.script_dir = Path(__file__).resolve().parent
        def handle_command_line(self): return False
        def get_translation(self, k, d): return d
    def get_color(n, d=""): return d
    def get_logic_dir(d): return d / "logic"

class TexTool(ToolBase):
    def __init__(self):
        super().__init__("TEX")
        self.logic_dir = get_logic_dir(self.script_dir)
        self.templates_dir = self.logic_dir / "templates"
        self.install_dir = self.project_root / "tool" / "TEX" / "data" / "install"

    def get_tex_bin_dir(self) -> Optional[Path]:
        """Find the bin directory within the local TinyTeX installation."""
        tinytex_root = self.install_dir / "TinyTeX"
        if not tinytex_root.exists():
            return None
        
        # Structure: TinyTeX/bin/<arch>/
        bin_root = tinytex_root / "bin"
        if bin_root.exists():
            for arch_dir in bin_root.iterdir():
                if arch_dir.is_dir():
                    return arch_dir
        return None

    def ensure_tex(self) -> bool:
        """Ensure pdflatex is available, either globally or locally."""
        if shutil.which("pdflatex"):
            return True
        
        local_bin = self.get_tex_bin_dir()
        if local_bin:
            os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
            return True
            
        return False

    def list_templates(self):
        """List all available templates."""
        BOLD, BLUE, RESET = get_color("BOLD"), get_color("BLUE"), get_color("RESET")
        
        if not self.templates_dir.exists():
            print(self.get_translation("tex_no_templates_dir", "No templates directory found."))
            return
            
        templates = [d.name for d in self.templates_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        if not templates:
            print(self.get_translation("tex_no_templates_found", "No templates found."))
            return
            
        print(f"--- {BOLD}{BLUE}" + self.get_translation("tex_available_templates", "Available Templates") + f"{RESET} ---")
        for t in sorted(templates):
            print(f"- {t}")

    def create_template(self, template_name: str, target_root: Optional[str] = None):
        """Create a new project from a template."""
        BOLD, GREEN, RED, YELLOW, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("YELLOW"), get_color("RESET")
        
        src_path = self.templates_dir / template_name
        if not src_path.exists() or not src_path.is_dir():
            print(f"{BOLD}{RED}" + self.get_translation("err_template_not_found", "Template '{name}' not found.").format(name=template_name) + f"{RESET}")
            return 1
            
        target_dir = Path(target_root or os.getcwd()).resolve()
        target_path = target_dir / template_name
        
        # Handle collisions with hash
        if target_path.exists():
            rand_hash = hashlib.md5(str(random.random()).encode()).hexdigest()[:8]
            target_path = target_dir / f"{template_name}-{rand_hash}"
            print(f"{BOLD}{YELLOW}" + self.get_translation("tex_target_collision", "Target directory exists, using randomized name: {path}").format(path=target_path.name) + f"{RESET}")
            
        try:
            shutil.copytree(src_path, target_path)
            print(f"{BOLD}{GREEN}" + self.get_translation("tex_template_created", "Successfully created project from template '{name}' at:").format(name=template_name) + f"{RESET} {target_path}")
            
            # Suggest compile command
            tex_files = list(target_path.glob("*.tex"))
            main_tex = tex_files[0].name if tex_files else "main.tex"
            
            print(f"\n" + self.get_translation("tex_compile_hint", "To compile this project, run:"))
            print(f"{BOLD}TEX compile {target_path / main_tex}{RESET}")
            return 0
        except Exception as e:
            print(f"{BOLD}{RED}" + self.get_translation("err_copy_failed", "Failed to create project: {error}").format(error=e) + f"{RESET}")
            return 1

    def compile(self, tex_file: str, output_dir: Optional[str] = None):
        """Compile a LaTeX file to PDF."""
        BOLD, GREEN, RED, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("RESET")
        
        if not self.ensure_tex():
            print(f"{BOLD}{RED}" + self.get_translation("err_no_tex", "Error: pdflatex not found. Please install TeX or run 'TEX setup'.") + f"{RESET}")
            return 1
            
        tex_path = Path(tex_file).resolve()
        if not tex_path.exists():
            print(f"{BOLD}{RED}" + self.get_translation("err_file_not_found", "File not found: {file}").format(file=tex_file) + f"{RESET}")
            return 1
            
        print(self.get_translation("tex_compiling", "Compiling {file}...").format(file=tex_path.name))
        
        # Base command
        cmd = ["pdflatex", "-interaction=nonstopmode", "-shell-escape", tex_path.name]
        
        # Run pdflatex twice for references (simplified logic)
        try:
            for i in range(2):
                res = subprocess.run(cmd, cwd=str(tex_path.parent), capture_output=True, text=True)
                if res.returncode != 0:
                    print(f"{BOLD}{RED}" + self.get_translation("err_compile_failed", "Compilation failed (Exit {code})").format(code=res.returncode) + f"{RESET}")
                    print(res.stdout[-500:]) # Show last part of log
                    return res.returncode
            
            pdf_file = tex_path.with_suffix(".pdf")
            if pdf_file.exists():
                final_path = pdf_file
                if output_dir:
                    out_path = Path(output_dir).resolve()
                    out_path.mkdir(parents=True, exist_ok=True)
                    final_path = out_path / pdf_file.name
                    shutil.move(str(pdf_file), str(final_path))
                
                print(f"{BOLD}{GREEN}" + self.get_translation("tex_compile_success", "Successfully compiled to:") + f"{RESET} {final_path}")
                return 0
            else:
                print(f"{BOLD}{RED}" + self.get_translation("err_pdf_missing", "Compilation finished but PDF was not found.") + f"{RESET}")
                return 1
        except Exception as e:
            print(f"{BOLD}{RED}" + self.get_translation("err_exec_failed", "Execution error: {error}").format(error=e) + f"{RESET}")
            return 1

def main():
    tool = TexTool()
    if tool.handle_command_line(): return 0
    
    parser = argparse.ArgumentParser(description="TEX - LaTeX Compilation and Template Manager")
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    
    # compile
    compile_p = subparsers.add_parser("compile", help="Compile .tex to .pdf")
    compile_p.add_argument("file", help="Path to .tex file")
    compile_p.add_argument("--output", "-o", help="Output directory")
    
    # list
    subparsers.add_parser("list", help="List available templates")
    
    # template
    template_p = subparsers.add_parser("template", help="Create project from template")
    template_p.add_argument("name", help="Template name")
    template_p.add_argument("--target", "-t", help="Target directory (default: current)")
    
    args = parser.parse_args()
    
    if args.command == "compile":
        return tool.compile(args.file, args.output)
    elif args.command == "list":
        tool.list_templates()
        return 0
    elif args.command == "template":
        return tool.create_template(args.name, args.target)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())

