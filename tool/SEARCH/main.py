#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEARCH Tool
- General web search and academic paper search.
- Replaces former SEARCH_PAPER tool.
"""

import os
import sys
import argparse
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
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
        self.results_dir = self.project_root / "tool" / "SEARCH" / "data" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def web_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Perform general web search using DuckDuckGo."""
        print(f"Searching web for: '{query}'...")
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return [{"title": r['title'], "url": r['href'], "snippet": r['body'], "source": "duckduckgo"} for r in results]
        except Exception as e:
            print(f"Web search error: {e}", file=sys.stderr)
            return []

    def paper_search(self, query: str, max_results: int = 5, sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Perform academic paper search (arXiv, Google Scholar)."""
        if not sources: sources = ["arxiv", "scholar"]
        
        all_papers = []
        if "arxiv" in sources:
            all_papers.extend(self._search_arxiv(query, max_results))
        
        if "scholar" in sources:
            all_papers.extend(self._search_scholar(query, max_results))
            
        # Deduplicate by title
        unique = []
        seen = set()
        for p in all_papers:
            t = p['title'].lower().strip()
            if t not in seen:
                seen.add(t)
                unique.append(p)
        
        return unique[:max_results]

    def _search_arxiv(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        print(f"Searching arXiv for: '{query}'...")
        papers = []
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"
            res = self.session.get(url, timeout=30)
            from xml.etree import ElementTree as ET
            root = ET.fromstring(res.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip()
                id_url = entry.find('atom:id', ns).text.strip()
                summary = entry.find('atom:summary', ns).text.strip()
                papers.append({
                    "title": title,
                    "url": id_url,
                    "snippet": summary[:200] + "...",
                    "source": "arxiv"
                })
        except Exception as e:
            print(f"arXiv error: {e}", file=sys.stderr)
        return papers

    def _search_scholar(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        print(f"Searching Google Scholar for: '{query}'...")
        papers = []
        try:
            url = f"https://scholar.google.com/scholar?q={query}&hl=en"
            res = self.session.get(url, timeout=30)
            soup = BeautifulSoup(res.content, 'html.parser')
            for entry in soup.find_all('div', class_='gs_r gs_or gs_scl')[:max_results]:
                title_elem = entry.find('h3', class_='gs_rt')
                if not title_elem: continue
                title = title_elem.get_text().strip()
                link = title_elem.find('a')['href'] if title_elem.find('a') else ""
                snippet = entry.find('div', class_='gs_rs').get_text().strip() if entry.find('div', class_='gs_rs') else ""
                papers.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet,
                    "source": "scholar"
                })
        except Exception as e:
            print(f"Google Scholar error: {e} (Likely blocked or rate-limited)", file=sys.stderr)
        return papers

    def save_and_print(self, results: List[Dict[str, Any]], query: str):
        """Save results to JSON and print to terminal."""
        BOLD, GREEN, BLUE, RESET = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("RESET")
        
        if not results:
            print(f"{BOLD}{get_color('RED')}No results found.{RESET}")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_{timestamp}.json"
        with open(self.results_dir / filename, 'w', encoding='utf-8') as f:
            json.dump({"query": query, "results": results}, f, indent=2, ensure_ascii=False)
            
        print(f"\n--- {BOLD}{BLUE}Search Results for: {query}{RESET} ---")
        for i, r in enumerate(results, 1):
            print(f"{BOLD}{i}. {r['title']}{RESET}")
            print(f"   URL: {r['url']}")
            print(f"   Source: {r['source']}")
            print(f"   {r['snippet']}\n")
            
        print(f"{BOLD}{GREEN}Results saved to:{RESET} {self.results_dir / filename}")

def main():
    tool = SearchTool()
    if tool.handle_command_line(): return 0
    
    parser = argparse.ArgumentParser(description="SEARCH - Multi-platform search tool")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max", "-m", type=int, default=5, help="Max results")
    parser.add_argument("--paper", "-p", action="store_true", help="Search academic papers")
    parser.add_argument("--source", help="Sources for paper search (arxiv,scholar)")
    
    args = parser.parse_args()
    
    if args.paper:
        sources = args.source.split(",") if args.source else None
        results = tool.paper_search(args.query, args.max, sources)
    else:
        results = tool.web_search(args.query, args.max)
        
    tool.save_and_print(results, args.query)
    return 0

if __name__ == "__main__":
    sys.exit(main())
