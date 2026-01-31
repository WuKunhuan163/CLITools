#!/usr/bin/env python3
import sys
from pathlib import Path

def get_tex_compiler_func():
    """Returns a function to compile LaTeX files."""
    from tool.TEX.main import compile_tex
    return compile_tex

def get_tex_templates_dir():
    """Returns the directory containing LaTeX templates."""
    return Path(__file__).resolve().parent.parent / "templates"

