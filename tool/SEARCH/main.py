#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEARCH Tool
- Multi-platform search tool for web and academic papers.
- Features parallel workers, filtering, and sorting for papers.
"""

import os
import sys
import argparse
import json
import time
import re
import threading
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

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

class SearchTool(ToolBase):
    def __init__(self):
        super().__init__("SEARCH")
        import requests
        from tool.SEARCH.logic.paper.searcher import PaperSearcher
        
        self.results_dir = self.project_root / "tool" / "SEARCH" / "data" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        self.paper_searcher = PaperSearcher(self.session)

    def web_search(self, query: str, max_results: int = 5, exact_match: bool = False) -> List[Dict[str, Any]]:
        """Perform general web search using DuckDuckGo (ddgs)."""
        BOLD, BLUE, RESET = get_color("BOLD"), get_color("BLUE"), get_color("RESET")
        
        # Exact match syntax support: if query has quotes, keep them
        search_query = query
        if exact_match and not (query.startswith('"') and query.endswith('"')):
            search_query = f'"{query}"'
            
        start_time = time.time()
        results = []
        stop_event = threading.Event()
        
        def update_timer():
            while not stop_event.is_set():
                elapsed = int(time.time() - start_time)
                sys.stdout.write(f"\r\033[K{BOLD}{BLUE}Searching web{RESET} for: '{query}'... ({elapsed}s)")
                sys.stdout.flush()
                time.sleep(1)
        
        timer_thread = threading.Thread(target=update_timer, daemon=True)
        timer_thread.start()
        
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=max_results))
        except: pass
        finally:
            stop_event.set()
            timer_thread.join(timeout=0.1)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            
        return [{"title": r['title'], "url": r['href'], "snippet": r['body'], "source": "duckduckgo"} for r in results]

    def paper_search(self, query: str, max_results: int = 5, sources: Optional[List[str]] = None,
                     sort_by: str = "relevance", min_citations: int = 0, min_year: int = 0,
                     exact_match: bool = False) -> List[Dict[str, Any]]:
        """Perform parallel academic paper search (arXiv, Google Scholar)."""
        if not sources: sources = ["arxiv", "scholar"]
        
        BOLD, BLUE, WHITE, RESET = get_color("BOLD"), get_color("BLUE"), get_color("WHITE", "\033[37m"), get_color("RESET")
        start_time = time.time()
        all_papers = []
        stop_event = threading.Event()
        
        # Refined exact match detection: if query starts/ends with quotes, use exact match
        if query.startswith('"') and query.endswith('"'):
            exact_match = True
            query = query[1:-1] # Strip quotes for internal processing
            
        def update_timer():
            while not stop_event.is_set():
                elapsed = int(time.time() - start_time)
                sys.stdout.write(f"\r\033[K{BOLD}{BLUE}Searching papers{RESET} for: '{query}'... ({elapsed}s)")
                sys.stdout.flush()
                time.sleep(1)
        
        timer_thread = threading.Thread(target=update_timer, daemon=True)
        timer_thread.start()
        
        results_info = [] # Store (source_name, count)
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
                future_to_src = {}
                if "arxiv" in sources:
                    future_to_src[executor.submit(self.paper_searcher.search_arxiv, query, max_results * 2, exact_match)] = "arXiv"
                if "scholar" in sources:
                    future_to_src[executor.submit(self.paper_searcher.search_scholar, query, max_results * 2, exact_match)] = "Google Scholar"
                
                for future in concurrent.futures.as_completed(future_to_src):
                    src_name = future_to_src[future]
                    try:
                        papers = future.result()
                        all_papers.extend(papers)
                        results_info.append((src_name, len(papers)))
                    except: pass
        finally:
            stop_event.set()
            timer_thread.join(timeout=0.1)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            
        # Display individual results
        for src, count in results_info:
            label = self.get_translation("label_successfully_received_from", "Successfully received search results from")
            print(f"{BOLD}{WHITE}{label}{RESET} {src} ({count}).")
            
        # Deduplicate by title
        unique = []
        seen = set()
        for p in all_papers:
            t = p['title'].lower().strip()
            if t not in seen:
                seen.add(t)
                unique.append(p)
        
        # Filtering and Sorting
        from tool.SEARCH.logic.paper.searcher import filter_and_sort_papers
        final_papers = filter_and_sort_papers(unique, query, sort_by, min_citations, min_year)
        
        return final_papers[:max_results]

    def save_and_print(self, results: List[Dict[str, Any]], query: str):
        """Save results to JSON and print to terminal."""
        BOLD, GREEN, BLUE, WHITE, RESET = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("WHITE", "\033[37m"), get_color("RESET")
        
        if not results:
            print(f"{BOLD}{get_color('RED')}No results found.{RESET}")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_{timestamp}.json"
        with open(self.results_dir / filename, 'w', encoding='utf-8') as f:
            json.dump({"query": query, "results": results}, f, indent=2, ensure_ascii=False)
            
        # Only bold 'Successfully received' as requested
        success_label = self.get_translation("label_successfully_received", "Successfully received")
        print(f"\n{BOLD}{GREEN}{success_label}{RESET} search results: {query}\n")
        
        for i, r in enumerate(results, 1):
            print(f"{BOLD}{i}. {r['title']}{RESET}")
            print(f"   URL: {r['url']}")
            print(f"   Source: {r['source']}")
            # Display citations/year if available
            info = []
            if r.get('citations') is not None: info.append(f"Citations: {r['citations']}")
            if r.get('year'): info.append(f"Year: {r['year']}")
            if info: print(f"   ({', '.join(info)})")
            
            print(f"   {r['snippet']}\n")
            
        saved_label = self.get_translation("label_results_saved", "Results saved to")
        print(f"{BOLD}{WHITE}{saved_label}{RESET}: {self.results_dir / filename}")

def main():
    tool = SearchTool()
    if tool.handle_command_line(): return 0
    
    parser = argparse.ArgumentParser(description="SEARCH - Multi-platform search tool")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max", "-m", type=int, default=5, help="Max results")
    parser.add_argument("--paper", "-p", action="store_true", help="Search academic papers")
    parser.add_argument("--source", help="Sources for paper search (arxiv,scholar)")
    parser.add_argument("--sort", choices=["relevance", "citations", "title", "date"], default="relevance", help="Sort criteria")
    parser.add_argument("--min-citations", type=int, default=0, help="Minimum citations (for papers)")
    parser.add_argument("--min-year", type=int, default=0, help="Minimum publication year")
    parser.add_argument("--exact", "-e", action="store_true", help="Enforce exact match")
    
    args = parser.parse_args()
    
    if args.paper:
        sources = args.source.split(",") if args.source else None
        results = tool.paper_search(args.query, args.max, sources, args.sort, args.min_citations, args.min_year, args.exact)
    else:
        results = tool.web_search(args.query, args.max, args.exact)
        
    tool.save_and_print(results, args.query)
    return 0

if __name__ == "__main__":
    sys.exit(main())
