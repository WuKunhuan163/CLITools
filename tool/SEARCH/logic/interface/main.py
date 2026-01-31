#!/usr/bin/env python3
import sys
from pathlib import Path

def get_paper_searcher_class():
    """Returns the PaperSearcher class."""
    from tool.SEARCH.logic.paper.searcher import PaperSearcher
    return PaperSearcher

def get_web_search_func():
    """Returns a function for general web search."""
    from tool.SEARCH.main import web_search
    return web_search

