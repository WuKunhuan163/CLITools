"""Semantic search infrastructure for tools, interfaces, and skills.

Provides a unified API for discovering project components by meaning
rather than exact text matching.  Built on TF-IDF with no external
dependencies — everything uses the standard library.

Quick start::

    from logic.search import search_tools, search_interfaces, search_skills

    results = search_tools(project_root, "open a Chrome tab")
    # => [{"id": "GOOGLE.CDMCP", "score": 0.87, "meta": {...}}, ...]

For lower-level access::

    from logic.search.semantic import SemanticIndex

    idx = SemanticIndex()
    idx.add("doc1", "some text content", {"type": "custom"})
    results = idx.search("query text")
"""
from logic.search.semantic import SemanticIndex
from logic.search.tools import (
    search_tools,
    search_interfaces,
    search_skills,
    build_tool_index,
    build_interface_index,
    build_skill_index,
)

__all__ = [
    "SemanticIndex",
    "search_tools",
    "search_interfaces",
    "search_skills",
    "build_tool_index",
    "build_interface_index",
    "build_skill_index",
]
