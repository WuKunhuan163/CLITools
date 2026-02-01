#!/usr/bin/env python3
import argparse
import sys
import time
import json
import threading
from datetime import datetime
import hashlib
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from logic.tool.base import ToolBase
from logic.turing.models.worker import ParallelWorkerPool
from logic.config.tool_config_manager import ToolConfigManager

class ReadTool(ToolBase):
    def __init__(self):
        super().__init__("READ")
        self.image_metadata = []
        self.page_stats = {}
        self.meta_lock = threading.Lock()
        self.config_manager = ToolConfigManager(self.tool_name, self.script_dir)

    def format_page_list(self, pages: list) -> str:
        """Format a list of page numbers into compact ranges (e.g., 1-3, 5, 7-10)."""
        if not pages: return ""
        pages = sorted(list(set(pages)))
        ranges = []
        start = pages[0]
        end = pages[0]
        for i in range(1, len(pages)):
            if pages[i] == end + 1: end = pages[i]
            else:
                ranges.append(str(start) if start == end else f"{start}-{end}")
                start = end = pages[i]
        ranges.append(str(start) if start == end else f"{start}-{end}")
        return ", ".join(ranges)

    def run(self):
        if self.handle_command_line(): return

        parser = argparse.ArgumentParser(description=self.get_translation("tool_READ_desc", "Read and extract content from PDF, Word, and images."))
        
        # Subparsers for commands like 'config'
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Config command
        config_parser = subparsers.add_parser("config", help="Configure READ tool settings")
        config_parser.add_argument("--alpha", type=float, help="Set alpha transparency for PDF semantic visualization (0.0-1.0)")

        # Main extraction command (default)
        extract_parser = subparsers.add_parser("extract", help="Extract content from a file", conflict_handler='resolve')
        extract_parser.add_argument("file", nargs="?", help="Path to the file to read")
        extract_parser.add_argument("-o", "--output", help="Output directory path (optional)")
        extract_parser.add_argument("--page", help="Specific page(s) to extract (e.g. 7, 1-5)")
        extract_parser.add_argument("-n", "--workers", type=int, default=4, help="Number of parallel workers (default: 4)")
        extract_parser.add_argument("--mode", default="academic", choices=["academic", "general", "code_snippet", "formula", "table"], help="Vision analysis mode for images")
        extract_parser.add_argument("--key", help="Google API Key (overrides env vars)")
        extract_parser.add_argument("--test-vision", action="store_true", help="Test vision API connectivity")
        
        args, unknown = parser.parse_known_args()

        if args.command == "config":
            if args.alpha is not None:
                if 0.0 <= args.alpha <= 1.0:
                    self.config_manager.set("pdf.visual_alpha", args.alpha)
                    print(f"{self.get_color('GREEN')}Config updated{self.get_color('RESET')}: pdf.visual_alpha = {args.alpha}")
                else:
                    print(f"{self.get_color('RED')}Error{self.get_color('RESET')}: Alpha value must be between 0.0 and 1.0.")
            else:
                print(f"Current config: pdf.visual_alpha = {self.config_manager.get('pdf.visual_alpha', 0.20)}")
            return

        # If no command is specified, assume 'extract'
        if args.command is None:
            # Re-parse with 'extract' as default command
            sys.argv.insert(1, "extract")
            args = parser.parse_args()

        if args.test_vision:
            from tool.READ.logic.vision.gemini import GeminiAnalyzer
            analyzer = GeminiAnalyzer(api_key=args.key)
            results = analyzer.test_connection()
            print(json.dumps(results, indent=2))
            return

        if not args.file:
            parser.print_help()
            return

        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"{self.get_color('RED')}{self.get_translation('label_error', 'Error')}{self.get_color('RESET')}: " + 
                  self.get_translation("error_file_not_found", f"File not found: {args.file}"))
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = hashlib.md5(f"{file_path}{time.time()}".encode()).hexdigest()[:8]
        result_dir_name = f"result_{timestamp}_{unique_id}"
        
        default_data_dir = self.script_dir / "data" / "pdf"
        output_dir = Path(args.output).resolve() if args.output else default_data_dir / result_dir_name
        pages_dir = output_dir / "pages"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        pages_dir.mkdir(parents=True, exist_ok=True)

        info = {
            "source_file": str(file_path),
            "timestamp": timestamp,
            "extraction_mode": "basic",
            "pages": {},
            "images": []
        }

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
            
            # Get alpha from config
            visual_alpha = self.config_manager.get("pdf.visual_alpha", 0.20)
            alpha_int = int(visual_alpha * 255) # Convert 0.0-1.0 to 0-255

            tasks = []
            for p_num in pages:
                tasks.append({
                    "id": str(p_num + 1),
                    "action": self._extract_pdf_page_task,
                    "args": (file_path, p_num, pages_dir, median_size, alpha_int)
                })
            
            def on_page_finish(page_id, result):
                with self.meta_lock:
                    self.page_stats[page_id] = result
                    if result["success"]:
                        success_pages.append(int(page_id))
                        if result.get("images"):
                            self.image_metadata.extend(result["images"])
                    else:
                        failed_pages.append(int(page_id))

            pool.run(tasks, success_callback=on_page_finish)
            info["pages"] = self.page_stats
            info["images"] = self.image_metadata

        elif suffix == ".docx":
            from tool.READ.logic.docx import extract_docx
            images_dir = output_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            try:
                content = extract_docx(file_path, images_dir)
                doc_md = pages_dir / "document.md"
                with open(doc_md, "w", encoding="utf-8") as f:
                    f.write(content)
                success_pages = [1]
                info["pages"]["1"] = {"success": True, "word_count": len(content.split()), "size_bytes": doc_md.stat().st_size}
            except Exception as e:
                failed_pages = [1]
                info["pages"]["1"] = {"success": False, "error": str(e)}

        elif suffix in [".png", ".jpg", ".jpeg", ".webp"]:
            from tool.READ.logic.vision.gemini import GeminiAnalyzer
            analyzer = GeminiAnalyzer(api_key=args.key)
            sys.stdout.write(f"\r\033[K{self.get_color('BOLD')}{self.get_color('BLUE')}Analyzing image{self.get_color('RESET')} {file_path.name}...")
            sys.stdout.flush()
            
            res = analyzer.analyze_image(file_path, mode=args.mode)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            
            if res["success"]:
                analysis_md = pages_dir / "analysis.md"
                with open(analysis_md, "w", encoding="utf-8") as f:
                    f.write(f"# Vision Analysis: {file_path.name}\n\n")
                    f.write(res["result"])
                success_pages = [1]
                info["vision_analysis"] = {
                    "mode": args.mode,
                    "key_used": res.get("key_type"),
                    "word_count": len(res["result"].split()),
                    "size_bytes": analysis_md.stat().st_size
                }
                info["pages"]["1"] = {"success": True}
            else:
                print(f"{self.get_color('BOLD')}{self.get_color('RED')}Vision Error{self.get_color('RESET')}: {res['error']}")
                failed_pages = [1]
                info["pages"]["1"] = {"success": False, "error": res["error"]}
        else:
            print(f"{self.get_color('RED')}{self.get_translation('label_error', 'Error')}{self.get_color('RESET')}: Unsupported file type: {suffix}")
            return

        with open(output_dir / "info.json", "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

        # Cache management
        from logic.utils import cleanup_old_files
        cleanup_old_files(default_data_dir, "result_*", limit=1024, batch_size=512)

        # Final Summary
        duration = time.time() - start_time
        BOLD, GREEN, RED, RESET = self.get_color('BOLD', '\033[1m'), self.get_color('GREEN', '\033[32m'), self.get_color('RED', '\033[31m'), self.get_color('RESET', '\033[0m')
        
        if failed_pages:
            failed_label = self.get_translation("label_failed_to_extract", "Failed to extract")
            print(f"\r\033[K{BOLD}{RED}{failed_label}{RESET} {self.get_translation('label_pages', 'pages')} {self.format_page_list(failed_pages)} in {file_path.name}")

        if success_pages:
            success_label = self.get_translation("label_successfully_extracted", "Successfully extracted")
            print(f"\r\033[K{BOLD}{GREEN}{success_label}{RESET} {self.get_translation('label_pages', 'pages')} {self.format_page_list(success_pages)} in {file_path.name} ({duration:.2f}s)")

        print(f"{BOLD}{self.get_translation('label_results_saved_to', 'Results saved to')}:{RESET} {output_dir}")

    def _extract_pdf_page_task(self, pdf_path, page_num, pages_dir, median_size, alpha_int):
        """Task to extract a single page. Returns dict with metadata and stats."""
        import fitz
        from tool.READ.logic.pdf.extractor import extract_single_pdf_page
        actual_page_num = page_num + 1
        try:
            doc = fitz.open(str(pdf_path))
            content, meta, semantic = extract_single_pdf_page(doc, page_num, pages_dir, median_size, alpha_int)
            doc.close()
            
            # The markdown file is now created inside extract_single_pdf_page
            page_file = pages_dir / f"page_{actual_page_num:03d}" / "extracted.md"
            
            if page_file.exists() and page_file.stat().st_size > 0:
                return {
                    "success": True,
                    "word_count": len(content.split()),
                    "size_bytes": page_file.stat().st_size,
                    "images": meta,
                    "semantic_blocks": semantic
                }
            return {"success": False, "error": "File creation failed or empty"}
        except Exception as e:
            return {"success": False, "error": str(e)}

def main():
    tool = ReadTool()
    tool.run()

if __name__ == "__main__":
    main()
