#!/usr/bin/env python3
import sys
import argparse
import os
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage

class ReadTool(ToolBase):
    def __init__(self):
        super().__init__("READ")

    def run(self):
        if self.handle_command_line(): return

        parser = argparse.ArgumentParser(description=self.get_translation("tool_READ_desc", "Read and extract content from PDF, Word, and images."))
        parser.add_argument("file", nargs="?", help="Path to the file to read")
        parser.add_argument("-o", "--output", help="Output markdown file path")
        parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
        
        args, unknown = parser.parse_known_args()

        if args.demo:
            self.show_demo()
            return

        if not args.file:
            parser.print_help()
            return

        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"{self.get_color('RED')}{self.get_translation('label_error', 'Error')}{self.get_color('RESET')}: " + 
                  self.get_translation("error_file_not_found", "File not found: {file}", file=args.file))
            return

        output_file = Path(args.output).resolve() if args.output else file_path.with_suffix(".md")
        images_dir = output_file.parent / "images"

        tm = ProgressTuringMachine()
        
        def do_extract():
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                from tool.READ.logic.pdf import extract_pdf
                content = extract_pdf(file_path, images_dir)
            elif suffix == ".docx":
                from tool.READ.logic.docx import extract_docx
                content = extract_docx(file_path, images_dir)
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
                
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        tm.add_stage(TuringStage(
            name="Extraction",
            action=do_extract,
            active_status=self.get_translation("label_extracting", "Extracting"),
            success_status=self.get_translation("label_successfully", "Successfully") + " " + self.get_translation("label_extracted", "extracted"),
            fail_status=self.get_translation("label_failed", "Failed"),
            bold_part=self.get_translation("label_extracting", "Extracting")
        ))

        if tm.run():
            print(f"\n{self.get_color('BOLD')}{self.get_translation('label_results_saved_to', 'Results saved to')}:{self.get_color('RESET')} {output_file}")

    def show_demo(self):
        BOLD = self.get_color("BOLD")
        GREEN = self.get_color("GREEN")
        BLUE = self.get_color("BLUE")
        RESET = self.get_color("RESET")
        print(f"{BOLD}{BLUE}Progressing{RESET}... {BOLD}{GREEN}Successfully{RESET} finished!")

def main():
    tool = ReadTool()
    tool.run()

if __name__ == "__main__":
    main()
