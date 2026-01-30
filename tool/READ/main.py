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
        parser.add_argument("--page", help="Specific page(s) to extract (e.g. 7, 1-5)")
        
        args, unknown = parser.parse_known_args()

        if not args.file:
            parser.print_help()
            return

        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"{self.get_color('RED')}{self.get_translation('label_error', 'Error')}{self.get_color('RESET')}: " + 
                  self.get_translation("error_file_not_found", "File not found: {file}", file=args.file))
            return

        # Default output directory: tool/READ/data/pdf/result_xxx_yyy/
        import time
        from datetime import datetime
        import hashlib
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = hashlib.md5(f"{file_path}{time.time()}".encode()).hexdigest()[:8]
        result_dir_name = f"result_{timestamp}_{unique_id}"
        
        default_data_dir = self.script_dir / "data" / "pdf"
        output_dir = default_data_dir / result_dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if args.output:
            output_file = Path(args.output).resolve()
        else:
            output_file = output_dir / "text.md"
            
        images_dir = output_dir / "images"

        tm = ProgressTuringMachine()
        start_time = time.time()
        
        def do_extract():
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                from tool.READ.logic.pdf import extract_pdf
                content = extract_pdf(file_path, images_dir, page_spec=args.page)
            elif suffix == ".docx":
                from tool.READ.logic.docx import extract_docx
                content = extract_docx(file_path, images_dir)
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
                
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Cache management: limit 1024, clean 512
            from logic.utils import cleanup_old_files
            cleanup_old_files(default_data_dir, "result_*", limit=1024, batch_size=512)
                
            return True

        tm.add_stage(TuringStage(
            name=file_path.name,
            action=do_extract,
            active_status=self.get_translation("label_extracting", "Extracting"),
            success_status=self.get_translation("label_successfully", "Successfully") + " " + self.get_translation("label_extracted", "extracted"),
            fail_status=self.get_translation("label_failed", "Failed"),
            bold_part=self.get_translation("label_extracting", "Extracting")
        ))

        if tm.run():
            duration = time.time() - start_time
            # Final success message with duration, formatted precisely
            success_label = self.get_translation('label_successfully', 'Successfully')
            extracted_label = self.get_translation('label_extracted', 'extracted')
            # Use \r\033[K to ensure we overwrite the last stage's transient status
            print(f"\r\033[K{self.get_color('BOLD')}{self.get_color('GREEN')}{success_label} {extracted_label}{self.get_color('RESET')} {file_path.name} ({duration:.2f}s)")
            
            # Print result path without empty line
            print(f"{self.get_color('BOLD')}{self.get_translation('label_results_saved_to', 'Results saved to')}:{self.get_color('RESET')} {output_file}")

def main():
    tool = ReadTool()
    tool.run()

if __name__ == "__main__":
    main()
