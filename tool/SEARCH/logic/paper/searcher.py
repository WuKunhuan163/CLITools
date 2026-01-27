from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import sys
import threading
import time
from pathlib import Path

class PaperSearcher:
    def __init__(self, session):
        self.session = session

    def search_arxiv(self, query: str, max_results: int, exact_match: bool = False) -> List[Dict[str, Any]]:
        papers = []
        try:
            import requests
            # ArXiv API supports 'all' prefix. For exact match, we'll filter later.
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results * 2}&sortBy=relevance&sortOrder=descending"
            res = self.session.get(url, timeout=30)
            from xml.etree import ElementTree as ET
            root = ET.fromstring(res.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip()
                id_url = entry.find('atom:id', ns).text.strip()
                summary = entry.find('atom:summary', ns).text.strip()
                published = entry.find('atom:published', ns).text.strip()
                year = int(published[:4]) if published else None
                
                # Check for exact match if requested
                if exact_match and query.lower() not in title.lower():
                    continue
                    
                papers.append({
                    "title": title,
                    "url": id_url,
                    "snippet": summary[:300] + "...",
                    "source": "arXiv",
                    "citations": None, # arXiv doesn't provide citations directly
                    "year": year
                })
        except: pass
        return papers[:max_results]

    def search_scholar(self, query: str, max_results: int, exact_match: bool = False) -> List[Dict[str, Any]]:
        papers = []
        try:
            from bs4 import BeautifulSoup
            import requests
            search_query = f'"{query}"' if exact_match else query
            url = f"https://scholar.google.com/scholar?q={search_query}&hl=en"
            res = self.session.get(url, timeout=30)
            soup = BeautifulSoup(res.content, 'html.parser')
            for entry in soup.find_all('div', class_='gs_r gs_or gs_scl'):
                title_elem = entry.find('h3', class_='gs_rt')
                if not title_elem: continue
                title = title_elem.get_text().strip()
                link = title_elem.find('a')['href'] if title_elem.find('a') else ""
                snippet = entry.find('div', class_='gs_rs').get_text().strip() if entry.find('div', class_='gs_rs') else ""
                
                # Citations
                citations = 0
                citation_elem = entry.find('div', class_='gs_fl')
                if citation_elem:
                    cite_link = citation_elem.find('a', string=re.compile(r'Cited by'))
                    if cite_link:
                        match = re.search(r'(\d+)', cite_link.get_text())
                        if match: citations = int(match.group(1))
                
                # Year
                year = None
                meta_elem = entry.find('div', class_='gs_a')
                if meta_elem:
                    match = re.search(r'(\d{4})', meta_elem.get_text())
                    if match: year = int(match.group(1))
                
                papers.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet,
                    "source": "Google Scholar",
                    "citations": citations,
                    "year": year
                })
                if len(papers) >= max_results: break
        except: pass
        return papers

def filter_and_sort_papers(papers: List[Dict[str, Any]], query: str, sort_by: List[str] = None, 
                          min_citations: int = 0, min_year: int = 0) -> List[Dict[str, Any]]:
    """Filter and sort paper results based on user preferences."""
    if sort_by is None: sort_by = ["relevance"]
    
    # 1. Filtering
    filtered = []
    for p in papers:
        # Citation filter
        if min_citations > 0:
            if p['citations'] is not None and p['citations'] < min_citations:
                continue
        
        # Year filter
        if min_year > 0:
            if p['year'] is not None and p['year'] < min_year:
                continue
        
        filtered.append(p)
        
    # 2. Sorting
    # Multiple sort criteria support: primary, secondary, etc.
    def get_sort_key(p):
        keys = []
        for criteria in sort_by:
            if criteria == "citations":
                keys.append(-(p['citations'] or 0))
            elif criteria == "title":
                from difflib import SequenceMatcher
                keys.append(-SequenceMatcher(None, query.lower(), p['title'].lower()).ratio())
            elif criteria == "date":
                keys.append(-(p['year'] or 0))
            elif criteria == "relevance":
                # Default relevance: mix of title overlap and year
                from difflib import SequenceMatcher
                overlap = SequenceMatcher(None, query.lower(), p['title'].lower()).ratio()
                year_score = (p['year'] - 2000) / 30 if p['year'] else 0
                keys.append(-(overlap * 0.7 + year_score * 0.3))
        return tuple(keys)

    filtered.sort(key=get_sort_key)
    
    return filtered

