#!/usr/bin/env python3
import argparse
import sys
import time
from datetime import datetime
import hashlib
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from logic.tool.base import ToolBase
from logic.turing.models.worker import ParallelWorkerPool

class ReadTool(ToolBase):
    def __init__(self):
        super().__init__("READ")

    def run(self):
        if self.handle_command_line(): return

        parser = argparse.ArgumentParser(description=self.get_translation("tool_READ_desc", "Read and extract content from PDF, Word, and images."))
        parser.add_argument("file", nargs="?", help="Path to the file to read")
        parser.add_argument("-o", "--output", help="Output directory path (optional)")
        parser.add_argument("--page", help="Specific page(s) to extract (e.g. 7, 1-5)")
        parser.add_argument("-n", "--workers", type=int, default=4, help="Number of parallel workers (default: 4)")
        
        args, unknown = parser.parse_known_args()

        if not args.file:
            parser.print_help()
            return

        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"{self.get_color('RED')}{self.get_translation('label_error', 'Error')}{self.get_color('RESET')}: " + 
                  self.get_translation("error_file_not_found", f"File not found: {args.file}"))
            return

        # Output directory structure: result_xxx_yyy/pages/page_001.md
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = hashlib.md5(f"{file_path}{time.time()}".encode()).hexdigest()[:8]
        result_dir_name = f"result_{timestamp}_{unique_id}"
        
        default_data_dir = self.script_dir / "data" / "pdf"
        output_dir = Path(args.output).resolve() if args.output else default_data_dir / result_dir_name
        pages_dir = output_dir / "pages"
        images_dir = output_dir / "images"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        pages_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        suffix = file_path.suffix.lower()
        
        if suffix == ".pdf":
            import fitz
            from tool.READ.logic.pdf.extractor import parse_page_spec, get_median_font_size, extract_single_pdf_page
            
            doc = fitz.open(str(file_path))
            pages = parse_page_spec(args.page, doc.page_count)
            
            # Pre-calculate median size
            all_blocks = []
            for p_num in pages:
                all_blocks.extend(doc[p_num].get_text("dict")["blocks"])
            median_size = get_median_font_size(all_blocks)
            doc.close()

            # Using ParallelWorkerPool for parallel extraction
            extract_label = self.get_translation("label_extracting", "Extracting")
            pages_label = self.get_translation("label_pages", "pages")
            
            pool = ParallelWorkerPool(max_workers=args.workers, status_label=f"{extract_label} {pages_label}")
            
            tasks = []
            for p_num in pages:
                actual_page_num = p_num + 1
                tasks.append({
                    "id": str(actual_page_num),
                    "action": self._extract_pdf_page_task,
                    "args": (file_path, p_num, images_dir, median_size, pages_dir)
                })
            
            all_success = pool.run(tasks)
            
            if not all_success:
                label_failed = self.get_translation("label_failed", "Failed")
                label_extracted = self.get_translation("label_extracted", "extracted")
                print(f"{self.get_color('BOLD')}{self.get_color('RED')}{label_failed}{self.get_color('RESET')} {label_extracted} {file_path.name}")
                return

        elif suffix == ".docx":
            from tool.READ.logic.docx import extract_docx
            content = extract_docx(file_path, images_dir)
            page_file = pages_dir / "document.md"
            with open(page_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print(f"{self.get_color('RED')}{self.get_translation('label_error', 'Error')}{self.get_color('RESET')}: Unsupported file type: {suffix}")
            return

        # Cache management
        from logic.utils import cleanup_old_files
        cleanup_old_files(default_data_dir, "result_*", limit=1024, batch_size=512)

        # Final success message
        duration = time.time() - start_time
        success_label = self.get_translation('label_successfully', 'Successfully')
        extracted_label = self.get_translation('label_extracted', 'extracted')
        
        sys.stdout.write(f"\r\033[K{self.get_color('BOLD')}{self.get_color('GREEN')}{success_label} {extracted_label}{self.get_color('RESET')} {file_path.name} ({duration:.2f}s)\n")
        sys.stdout.flush()
        print(f"{self.get_color('BOLD')}{self.get_translation('label_results_saved_to', 'Results saved to')}:{self.get_color('RESET')} {output_dir}")

    def _extract_pdf_page_task(self, pdf_path, page_num, images_dir, median_size, pages_dir):
        """Task to extract a single page."""
        import fitz
        from tool.READ.logic.pdf.extractor import extract_single_pdf_page
        
        actual_page_num = page_num + 1
        page_file = pages_dir / f"page_{actual_page_num:03d}.md"
        
        try:
            doc = fitz.open(str(pdf_path))
            content = extract_single_pdf_page(doc, page_num, images_dir, median_size)
            doc.close()
            
            with open(page_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Verify file exists and is not empty
            if page_file.exists() and page_file.stat().st_size > 0:
                return True
            return False
        except:
            return False

def main():
    tool = ReadTool()
    tool.run()

if __name__ == "__main__":
    main()
