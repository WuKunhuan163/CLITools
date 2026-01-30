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

    def format_page_list(self, pages: list) -> str:
        """Format a list of page numbers into compact ranges (e.g., 1-3, 5, 7-10)."""
        if not pages:
            return ""
        pages = sorted(list(set(pages)))
        ranges = []
        if not pages:
            return ""
            
        start = pages[0]
        end = pages[0]
        
        for i in range(1, len(pages)):
            if pages[i] == end + 1:
                end = pages[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = pages[i]
                end = pages[i]
        
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
            
        return ", ".join(ranges)

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
        
        success_pages = []
        failed_pages = []

        if suffix == ".pdf":
            import fitz
            from tool.READ.logic.pdf.extractor import parse_page_spec, get_median_font_size
            
            doc = fitz.open(str(file_path))
            pages = parse_page_spec(args.page, doc.page_count)
            
            all_blocks = []
            for p_num in pages:
                all_blocks.extend(doc[p_num].get_text("dict")["blocks"])
            median_size = get_median_font_size(all_blocks)
            doc.close()

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
            
            # Using success_callback to track which ones finished
            def on_page_finish(page_id, result):
                if result:
                    success_pages.append(int(page_id))
                else:
                    failed_pages.append(int(page_id))

            pool.run(tasks, success_callback=on_page_finish)

        elif suffix == ".docx":
            from tool.READ.logic.docx import extract_docx
            try:
                content = extract_docx(file_path, images_dir)
                page_file = pages_dir / "document.md"
                with open(page_file, "w", encoding="utf-8") as f:
                    f.write(content)
                success_pages = [1] # Treat docx as a single logical page for summary
            except:
                failed_pages = [1]
        else:
            print(f"{self.get_color('RED')}{self.get_translation('label_error', 'Error')}{self.get_color('RESET')}: Unsupported file type: {suffix}")
            return

        # Cache management
        from logic.utils import cleanup_old_files
        cleanup_old_files(default_data_dir, "result_*", limit=1024, batch_size=512)

        # Final Summary messages
        duration = time.time() - start_time
        BOLD = self.get_color('BOLD', '\033[1m')
        GREEN = self.get_color('GREEN', '\033[32m')
        RED = self.get_color('RED', '\033[31m')
        RESET = self.get_color('RESET', '\033[0m')
        
        # 1. Failed message first if any
        if failed_pages:
            failed_label = self.get_translation("label_failed_to_extract", "Failed to extract")
            pages_str = self.format_page_list(failed_pages)
            pages_label = self.get_translation("label_pages", "pages")
            sys.stdout.write(f"\r\033[K{BOLD}{RED}{failed_label}{RESET} {pages_label} {pages_str} in {file_path.name}\n")

        # 2. Success message
        if success_pages:
            success_label = self.get_translation("label_successfully_extracted", "Successfully extracted")
            pages_str = self.format_page_list(success_pages)
            pages_label = self.get_translation("label_pages", "pages")
            sys.stdout.write(f"\r\033[K{BOLD}{GREEN}{success_label}{RESET} {pages_label} {pages_str} in {file_path.name} ({duration:.2f}s)\n")

        sys.stdout.flush()
        print(f"{BOLD}{self.get_translation('label_results_saved_to', 'Results saved to')}:{RESET} {output_dir}")

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
