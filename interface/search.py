"""Semantic search interface.

Provides tool, interface, skill, lesson, and discovery semantic search.

Quick start::

    from interface.search import search_tools, search_lessons, KnowledgeManager

    results = search_tools(project_root, "open a Chrome tab")
    lessons = search_lessons(project_root, "rate limiting")

    km = KnowledgeManager(project_root)
    results = km.search("rate limiting", scope="all", top_k=5)
"""
from logic._.search.tools import (
    search_tools,
    search_interfaces,
    search_skills,
    search_tools_deep,
)
from logic._.search.knowledge import KnowledgeManager


def search_lessons(project_root, query: str, top_k: int = 5, tool: str = None):
    """Search lessons by semantic similarity."""
    km = KnowledgeManager(project_root)
    return km.search(query, scope="lessons", top_k=top_k, tool=tool)


def search_discoveries(project_root, query: str, top_k: int = 5, tool: str = None):
    """Search discoveries by semantic similarity."""
    km = KnowledgeManager(project_root)
    return km.search(query, scope="discoveries", top_k=top_k, tool=tool)


def search_docs(project_root, query: str, top_k: int = 10):
    """Search project documentation (root docs, logic/, interface/ READMEs)."""
    km = KnowledgeManager(project_root)
    return km.search(query, scope="docs", top_k=top_k)


def search_all(project_root, query: str, top_k: int = 10, tool: str = None):
    """Search across all knowledge tiers (tools, skills, lessons, discoveries, docs)."""
    km = KnowledgeManager(project_root)
    return km.search(query, scope="all", top_k=top_k, tool=tool)


__all__ = [
    "search_tools",
    "search_interfaces",
    "search_skills",
    "search_tools_deep",
    "search_lessons",
    "search_discoveries",
    "search_docs",
    "search_all",
    "KnowledgeManager",
]
