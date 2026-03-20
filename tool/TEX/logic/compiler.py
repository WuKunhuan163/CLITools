"""Markdown to PDF compilation using fpdf2.

Pure Python, no system dependencies. Renders Markdown with basic formatting:
headings, paragraphs, bold/italic, code blocks, lists, and horizontal rules.
"""
import re
from pathlib import Path
from fpdf import FPDF


class _ReportPDF(FPDF):
    """Custom PDF class for development reports."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, "AITerminalTools Development Report", align="R")
        self.ln(8)
        self.set_x(self.l_margin)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


_UNICODE_REPLACE = {
    "\u2192": "->", "\u2190": "<-", "\u2194": "<->",
    "\u2013": "-", "\u2014": "--", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "-",
    "\u2713": "[x]", "\u2717": "[ ]", "\u00a0": " ",
    "\u2502": "|", "\u251c": "|-", "\u2514": "+-", "\u2500": "-",
}


def _strip_md_formatting(text: str) -> str:
    """Remove Markdown inline formatting and replace Unicode chars."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    for uc, repl in _UNICODE_REPLACE.items():
        text = text.replace(uc, repl)
    text = text.encode("ascii", "replace").decode("ascii")
    return text


def compile_md_to_pdf(source: Path, output: Path):
    """Compile a Markdown file to PDF.

    Args:
        source: Path to Markdown file.
        output: Path to output PDF file.
    """
    content = source.read_text(encoding="utf-8")
    lines = content.split("\n")

    pdf = _ReportPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    in_code_block = False
    in_table = False
    table_data = []
    effective_w = pdf.w - pdf.l_margin - pdf.r_margin

    for line in lines:
        pdf.set_x(pdf.l_margin)
        if line.startswith("```"):
            in_code_block = not in_code_block
            if in_code_block:
                pdf.ln(2)
            else:
                pdf.ln(4)
            continue

        if in_code_block:
            pdf.set_font("Courier", "", 9)
            pdf.set_fill_color(245, 245, 245)
            pdf.set_text_color(60, 60, 60)
            clean = line.replace("\t", "    ")
            for uc, repl in _UNICODE_REPLACE.items():
                clean = clean.replace(uc, repl)
            clean = clean.encode("ascii", "replace").decode("ascii")
            pdf.multi_cell(0, 5, clean, fill=True)
            pdf.set_text_color(0, 0, 0)
            continue

        if line.startswith("|") and "|" in line[1:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue
            usable_w = pdf.w - 20
            n_cols = max(len(cells), 1)
            col_w = max(usable_w / n_cols, 20)
            if not in_table:
                in_table = True
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 8)
                for cell in cells:
                    text = _strip_md_formatting(cell)[:35]
                    pdf.cell(col_w, 6, text, border=1)
                pdf.ln()
            else:
                pdf.set_font("Helvetica", "", 8)
                for cell in cells:
                    text = _strip_md_formatting(cell)[:35]
                    pdf.cell(col_w, 6, text, border=1)
                pdf.ln()
            continue

        if in_table:
            in_table = False
            pdf.ln(2)

        stripped = line.strip()

        if stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 18)
            pdf.ln(4)
            pdf.multi_cell(0, 10, _strip_md_formatting(stripped[2:]))
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
            pdf.ln(4)
            continue

        if stripped.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.ln(6)
            pdf.multi_cell(0, 8, _strip_md_formatting(stripped[3:]))
            pdf.ln(2)
            continue

        if stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.ln(4)
            pdf.multi_cell(0, 7, _strip_md_formatting(stripped[4:]))
            pdf.ln(1)
            continue

        if stripped.startswith("---") or stripped.startswith("***"):
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y() + 2, pdf.w - 10, pdf.get_y() + 2)
            pdf.ln(6)
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            bullet_text = _strip_md_formatting(stripped[2:])
            pdf.multi_cell(0, 5, f"  - {bullet_text}")
            continue

        if re.match(r'^\d+\.\s', stripped):
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, _strip_md_formatting(stripped))
            continue

        if not stripped:
            pdf.ln(3)
            continue

        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _strip_md_formatting(stripped))

    output.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output))
