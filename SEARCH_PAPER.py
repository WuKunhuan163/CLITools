#!/usr/bin/env python3
"""
SEARCH_PAPER.py - Enhanced Academic Paper Search Tool
Supports interactive mode and multi-platform search (arXiv, Google Scholar)
"""

import os
import sys
import json
import argparse
import hashlib
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def get_interactive_query():
    """获取交互式查询输入"""
    print(f"=== Academic Paper Search Tool ===", file=sys.stderr)
    print(f"Enter your search query (or 'quit' to exit):", file=sys.stderr)
    print(file=sys.stderr)
    
    try:
        query = input("Search query: ").strip()
        if query.lower() in ['quit', 'exit', 'q']:
            return None
        if not query:
            print(f"Empty query. Please try again.", file=sys.stderr)
            return get_interactive_query()
        return query
    except (KeyboardInterrupt, EOFError):
        print(f"\nSearch cancelled.", file=sys.stderr)
        return None

class MultiPlatformPaperSearcher:
    """多平台论文搜索器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        self.output_dir = Path(__file__).parent / "SEARCH_PAPER_DATA"
        self.results_dir = self.output_dir / "results"
        self.papers_dir = self.output_dir / "papers"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.papers_dir.mkdir(parents=True, exist_ok=True)
    
    def search_papers(self, query: str, max_results: int = 10, sources: List[str] = None) -> Dict[str, Any]:
        """
        搜索论文
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            sources: 搜索源列表，默认为所有源
        
        Returns:
            搜索结果字典
        """
        if sources is None:
            sources = ['arxiv', 'google_scholar']
        
        all_papers = []
        source_results = {}
        
        # 搜索各个平台
        for source in sources:
            try:
                if source == 'arxiv':
                    papers = self.search_arxiv(query, max_results)
                elif source == 'google_scholar':
                    # 对于Google Scholar使用双重阈值机制
                    threshold = min(max_results, 10)  # 默认阈值10，但不超过max_results
                    max_eval = 100  # 默认最大评估100篇论文
                    papers = self.search_google_scholar(query, max_results, threshold, max_eval)
                else:
                    continue
                
                source_results[source] = len(papers)
                all_papers.extend(papers)
                
                # 添加延迟以避免被封
                time.sleep(1)
                
            except Exception as e:
                source_results[source] = f"Error: {str(e)}"
                print(f"Error searching {source}: {e}", file=sys.stderr)
                continue
        
        # 去重和排序
        unique_papers = self.remove_duplicates(all_papers)
        final_papers = unique_papers[:max_results]
        
        # 创建结果
        result = {
            "success": True,
            "query": query,
            "max_results": max_results,
            "total_papers_found": len(final_papers),
            "source_results": source_results,
            "papers": final_papers,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存结果
        self.save_results(result)
        
        return result
    
    def search_papers_with_thresholds(self, query: str, max_results: int = 10, sources: List[str] = None, 
                                    threshold: int = 10, max_eval: int = 100) -> Dict[str, Any]:
        """
        搜索论文（支持Google Scholar双重阈值机制）
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            sources: 搜索源列表，默认为所有源
            threshold: Google Scholar有效PDF论文数量阈值（默认10）
            max_eval: Google Scholar最大评估论文数量（默认100）
        
        Returns:
            搜索结果字典
        """
        if sources is None:
            sources = ['arxiv', 'google_scholar']
        
        all_papers = []
        source_results = {}
        
        # 搜索各个平台
        for source in sources:
            try:
                if source == 'arxiv':
                    papers = self.search_arxiv(query, max_results)
                elif source == 'google_scholar':
                    # 对于Google Scholar使用双重阈值机制
                    papers = self.search_google_scholar(query, max_results, threshold, max_eval)
                else:
                    continue
                
                source_results[source] = len(papers)
                all_papers.extend(papers)
                
                # 添加延迟以避免被封
                time.sleep(1)
                
            except Exception as e:
                source_results[source] = f"Error: {str(e)}"
                print(f"Error searching {source}: {e}", file=sys.stderr)
                continue
        
        # 去重和排序
        unique_papers = self.remove_duplicates(all_papers)
        final_papers = unique_papers[:max_results]
        
        # 创建结果
        result = {
            "success": True,
            "query": query,
            "max_results": max_results,
            "threshold": threshold,
            "max_eval": max_eval,
            "total_papers_found": len(final_papers),
            "source_results": source_results,
            "papers": final_papers,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存结果
        self.save_results(result)
        
        return result
    
    def search_arxiv(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """搜索arXiv，改进搜索策略以提高相关性"""
        papers = []
        
        try:
            # 改进的搜索策略：
            # 1. 主要在标题和摘要中搜索
            # 2. 按相关性排序
            # 3. 增加机器学习相关分类的权重
            
            search_parts = []
            search_parts.append(f"ti:{query}")  # 标题
            search_parts.append(f"abs:{query}")  # 摘要
            
            if any(keyword in query.lower() for keyword in ['machine learning', 'optimization', 'neural', 'deep learning', 'gradient']):
                search_parts.append("cat:cs.LG")
                search_parts.append("cat:cs.AI")
                search_parts.append("cat:stat.ML")
            
            if any(keyword in query.lower() for keyword in ['optimization', 'gradient', 'descent', 'sgd', 'adam']):
                search_parts.append("cat:math.OC")
            
            search_query = " OR ".join(search_parts)
            api_url = f"http://export.arxiv.org/api/query?search_query={search_query}&start=0&max_results={max_results * 2}&sortBy=relevance&sortOrder=descending"
            
            print(f"arXiv search query: {search_query}", file=sys.stderr)
            
            response = self.session.get(api_url, timeout=30)
            response.raise_for_status()
            
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            for entry in root.findall('atom:entry', namespaces):
                try:
                    paper = self.parse_arxiv_entry(entry, namespaces)
                    if paper and self.is_relevant_arxiv_paper(paper, query):
                        papers.append(paper)
                        if len(papers) >= max_results:
                            break
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"arXiv search error: {e}", file=sys.stderr)
        
        return papers
    
    def is_relevant_arxiv_paper(self, paper: Dict[str, Any], query: str) -> bool:
        """检查arXiv论文是否与查询相关"""
        try:
            title = paper.get('title', '').lower()
            abstract = paper.get('abstract', '').lower()
            query_lower = query.lower()
            query_keywords = set(query_lower.split())
            
            title_words = set(title.split())
            abstract_words = set(abstract.split())
            
            title_matches = len(query_keywords.intersection(title_words))
            abstract_matches = len(query_keywords.intersection(abstract_words))
            
            if title_matches > 0 or abstract_matches > 0:
                return True
            
            if any(keyword in query_lower for keyword in ['optimization', 'gradient', 'sgd', 'adam']):
                optimization_terms = ['optimization', 'gradient', 'descent', 'sgd', 'adam', 'optimizer', 'learning rate', 'convergence']
                if any(term in title or term in abstract for term in optimization_terms):
                    return True
            
            if any(keyword in query_lower for keyword in ['machine learning', 'neural', 'deep learning']):
                ml_terms = ['machine learning', 'neural', 'deep learning', 'classification', 'regression', 'training', 'model']
                if any(term in title or term in abstract for term in ml_terms):
                    return True
            
            return False
        except Exception:
            return True
    
    def search_google_scholar(self, query: str, max_results: int, threshold: int = 10, max_eval: int = 100) -> List[Dict[str, Any]]:
        """搜索Google Scholar，使用双重阈值机制"""
        papers = []
        evaluated_count = 0
        
        try:
            search_num = min(max_eval, 100)
            search_url = f"https://scholar.google.com/scholar?q={query}+filetype:pdf&hl=en&num={search_num}"
            
            print(f"Searching Google Scholar: threshold={threshold}, max_eval={max_eval}", file=sys.stderr)
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            paper_entries = soup.find_all('div', class_='gs_r gs_or gs_scl')
            
            for entry in paper_entries:
                try:
                    evaluated_count += 1
                    paper = self.parse_google_scholar_entry(entry)
                    if paper:
                        papers.append(paper)
                        if len(papers) >= threshold:
                            break
                    if evaluated_count >= max_eval:
                        break
                except Exception:
                    evaluated_count += 1
                    if evaluated_count >= max_eval:
                        break
                    continue
        except Exception as e:
            print(f"Google Scholar search error: {e}", file=sys.stderr)
        
        return papers
    
    def parse_arxiv_entry(self, entry, namespaces) -> Optional[Dict[str, Any]]:
        """解析arXiv条目"""
        try:
            title = entry.find('atom:title', namespaces).text.strip()
            authors = []
            for author in entry.findall('atom:author', namespaces):
                name = author.find('atom:name', namespaces)
                if name is not None:
                    authors.append(name.text.strip())
            
            summary = entry.find('atom:summary', namespaces)
            abstract = summary.text.strip() if summary is not None else ""
            id_elem = entry.find('atom:id', namespaces)
            url = id_elem.text.strip() if id_elem is not None else ""
            pdf_url = url.replace('/abs/', '/pdf/') + '.pdf' if url else ""
            published = entry.find('atom:published', namespaces)
            pub_date = published.text.strip()[:10] if published is not None else ""
            
            return {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "url": url,
                "pdf_url": pdf_url,
                "publication_date": pub_date,
                "venue": "arXiv preprint",
                "citation_count": None,
                "source": "arxiv"
            }
        except Exception:
            return None
    
    def parse_google_scholar_entry(self, entry) -> Optional[Dict[str, Any]]:
        """解析Google Scholar条目"""
        try:
            title_elem = entry.find('h3', class_='gs_rt')
            if not title_elem:
                return None
            
            title_link = title_elem.find('a')
            if title_link:
                title = title_link.get_text().strip()
                url = title_link.get('href', '')
            else:
                title = title_elem.get_text().strip()
                url = ""
            
            pdf_url = ""
            pdf_links = entry.find_all('a', href=True)
            for link in pdf_links:
                href = link.get('href', '')
                link_text = link.get_text().strip().lower()
                if (href.endswith('.pdf') or 'pdf' in link_text or '.pdf' in href):
                    if href.startswith('http'):
                        pdf_url = href
                        break
                    elif href.startswith('/'):
                        pdf_url = 'https://scholar.google.com' + href
                        break
            
            if not pdf_url:
                for link in pdf_links:
                    href = link.get('href', '')
                    if href and href.startswith('http') and href != url:
                        if any(domain in href.lower() for domain in ['arxiv.org', 'researchgate.net', 'academia.edu']):
                            if 'arxiv.org/abs/' in href:
                                pdf_url = href.replace('/abs/', '/pdf/') + '.pdf'
                                break
                            else:
                                pdf_url = href
                                break
            
            if not pdf_url or not self.validate_pdf_url(pdf_url):
                return None
            
            authors_elem = entry.find('div', class_='gs_a')
            authors, venue, pub_date = [], "", ""
            if authors_elem:
                text = authors_elem.get_text()
                parts = text.split(' - ')
                if len(parts) >= 2:
                    authors = [a.strip() for a in parts[0].split(',')]
                    venue_text = parts[1]
                    venue_match = re.search(r'^([^,]+)', venue_text)
                    if venue_match: venue = venue_match.group(1).strip()
                    date_match = re.search(r'(\d{4})', venue_text)
                    if date_match: pub_date = date_match.group(1)
            
            abstract_elem = entry.find('div', class_='gs_rs')
            abstract = abstract_elem.get_text().strip() if abstract_elem else ""
            
            citation_elem = entry.find('div', class_='gs_fl')
            citation_count = None
            if citation_elem:
                citation_link = citation_elem.find('a', string=re.compile(r'Cited by'))
                if citation_link:
                    citation_match = re.search(r'(\d+)', citation_link.get_text())
                    if citation_match: citation_count = int(citation_match.group(1))
            
            return {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "url": url,
                "pdf_url": pdf_url,
                "publication_date": pub_date,
                "venue": venue,
                "citation_count": citation_count,
                "source": "google_scholar"
            }
        except Exception:
            return None
    
    def validate_pdf_url(self, pdf_url: str) -> bool:
        """验证PDF URL是否可访问"""
        try:
            if not pdf_url or not pdf_url.startswith('http'): return False
            reliable_domains = ['arxiv.org', 'ieee.org', 'acm.org', 'springer.com', 'sciencedirect.com']
            if any(domain in pdf_url.lower() for domain in reliable_domains): return True
            try:
                response = self.session.head(pdf_url, timeout=5, allow_redirects=True)
                return 'pdf' in response.headers.get('content-type', '').lower() or response.status_code == 200
            except:
                return any(domain in pdf_url.lower() for domain in ['researchgate.net', 'academia.edu'])
        except Exception:
            return False
    
    def remove_duplicates(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重"""
        unique_papers, seen_titles = [], set()
        for paper in papers:
            title = paper.get('title', '').lower().strip()
            if title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(paper)
        return unique_papers
    
    def save_results(self, result: Dict[str, Any]):
        """保存搜索结果到JSON文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"search_results_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        for paper in result.get("papers", []):
            paper_title = re.sub(r'[^\w\s-]', '', paper.get("title", "untitled")).replace(" ", "_")
            paper_file = self.papers_dir / f"{paper_title}.json"
            with open(paper_file, 'w', encoding='utf-8') as f:
                json.dump(paper, f, ensure_ascii=False, indent=2)

def show_help():
    """显示帮助信息"""
    help_text = """SEARCH_PAPER - Academic Paper Search Tool

Usage: SEARCH_PAPER [query] [options]

Arguments:
  query                Search query (if not provided, interactive mode will start)

Options:
  --max-results N      Maximum number of results (default: 10)
  --sources LIST       Comma-separated list of sources: arxiv,google_scholar
  --help, -h           Show this help message

Examples:
  SEARCH_PAPER "machine learning"                 # Search all sources
  SEARCH_PAPER "deep learning" --max-results 20  # Limit results
  SEARCH_PAPER --help                             # Show help"""
    print(help_text)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(prog='SEARCH_PAPER')
    parser.add_argument("query", nargs='?', default=None)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--sources", type=str)
    parser.add_argument("--threshold", type=int, default=10)
    parser.add_argument("--max-eval", type=int, default=100)
    
    args = parser.parse_args()
    query = args.query
    sources = args.sources.split(',') if args.sources else None
    
    if query is None:
        print(f"Search query: ", file=sys.stderr, end="")
        query = input().strip()
        if not query:
            return 1
            
    searcher = MultiPlatformPaperSearcher()
    if 'google_scholar' in (sources or ['arxiv', 'google_scholar']):
        result = searcher.search_papers_with_thresholds(query, args.max_results, sources, args.threshold, args.max_eval)
    else:
        result = searcher.search_papers(query, args.max_results, sources)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
