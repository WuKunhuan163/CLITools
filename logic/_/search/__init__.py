"""Semantic search infrastructure for tools, interfaces, and skills.

Provides a unified API for discovering project components by meaning
rather than exact text matching.  Built on TF-IDF with no external
dependencies — everything uses the standard library.

Quick start::

    from logic._.search import search_tools, search_interfaces, search_skills

    results = search_tools(project_root, "open a Chrome tab")
    # => [{"id": "GOOGLE.CDMCP", "score": 0.87, "meta": {...}}, ...]

For lower-level access::

    from logic._.search.semantic import SemanticIndex

    idx = SemanticIndex()
    idx.add("doc1", "some text content", {"type": "custom"})
    results = idx.search("query text")
"""
from logic._.search.semantic import SemanticIndex
from logic._.search.tools import (
    search_tools,
    search_interfaces,
    search_skills,
    build_tool_index,
    build_interface_index,
    build_skill_index,
)
from logic._.search.knowledge import KnowledgeManager

__all__ = [
    "SemanticIndex",
    "KnowledgeManager",
    "search_tools",
    "search_interfaces",
    "search_skills",
    "build_tool_index",
    "build_interface_index",
    "build_skill_index",
]
