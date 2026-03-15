"""Agent memory management — flush, search, and daily notes.

Implements pre-compaction memory flush and memory tools that agents
can use to persist knowledge across sessions.
"""
import os
import datetime
from typing import Dict, List, Optional

from logic.agent.brain import (
    write_daily_note,
    write_memory,
    load_recent_daily,
    load_bootstrap,
    get_experience_dir,
)


FLUSH_PROMPT_EN = (
    "Your context window is nearing capacity. Before it resets, "
    "write any important facts, decisions, or progress to memory.\n\n"
    "Use write_memory for permanent facts and write_daily for session notes.\n"
    "If nothing needs saving, respond with NO_REPLY."
)

FLUSH_PROMPT_ZH = (
    "你的上下文窗口即将达到容量上限。在重置之前，"
    "请将重要的事实、决定或进展写入记忆。\n\n"
    "使用 write_memory 保存永久事实，write_daily 保存会话笔记。\n"
    "如果没有需要保存的内容，回复 NO_REPLY。"
)

MEMORY_TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "write_memory",
            "description": (
                "Write a permanent fact to memory. Use 'category' to organize into "
                "subdirectories (e.g. 'tools/git', 'patterns/error-handling'). "
                "Each category gets its own MEMORY.md. Periodically reorganize: "
                "move facts to specific categories and remove outdated entries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string",
                                "description": "The fact or knowledge to persist"},
                    "category": {"type": "string",
                                 "description": "Optional category path (e.g. 'tools/git'). "
                                                "Defaults to root MEMORY.md."},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_daily",
            "description": "Append a note to today's daily log (session-level memory).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string",
                                "description": "The note to append"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": (
                "Search all memory files (including subcategories) for relevant "
                "knowledge. Returns matched snippets with file paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string",
                              "description": "What to search for"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reorganize_memory",
            "description": (
                "List all memory categories and their sizes. Use this to understand "
                "memory structure before reorganizing. When memory files grow large, "
                "split them into categories. Delete outdated facts."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


class MemoryHandlers:
    """Tool handlers for memory operations."""

    def __init__(self, project_root: str, brain_type: str = "default"):
        self._project_root = project_root
        self._brain_type = brain_type

    def handle_write_memory(self, args: dict) -> dict:
        content = args.get("content", "")
        category = args.get("category", "")
        if not content:
            return {"ok": False, "output": "No content provided."}
        write_memory(self._project_root, content, self._brain_type,
                     category=category)
        target = f"{category}/MEMORY.md" if category else "MEMORY.md"
        return {"ok": True, "output": f"Written to {target} ({len(content)} chars)."}

    def handle_write_daily(self, args: dict) -> dict:
        content = args.get("content", "")
        if not content:
            return {"ok": False, "output": "No content provided."}
        write_daily_note(self._project_root, content, self._brain_type)
        today = datetime.date.today().isoformat()
        return {"ok": True, "output": f"Appended to daily/{today}.md ({len(content)} chars)."}

    def handle_recall_memory(self, args: dict) -> dict:
        """Search all memory files including subcategories."""
        query = args.get("query", "").lower()
        if not query:
            return {"ok": False, "output": "No query provided."}

        exp_dir = get_experience_dir(self._project_root, self._brain_type)
        if not exp_dir.exists():
            return {"ok": True, "output": "(No memory files found.)"}

        all_md = _collect_memory_files(exp_dir)
        results = _search_files(all_md, query, exp_dir)

        if not results:
            return {"ok": True, "output": f"No matches for '{query}' in memory files."}
        return {"ok": True, "output": "\n---\n".join(results[:8])}

    def handle_reorganize_memory(self, args: dict) -> dict:
        """List all memory categories and sizes for reorganization."""
        exp_dir = get_experience_dir(self._project_root, self._brain_type)
        if not exp_dir.exists():
            return {"ok": True, "output": "(No memory directory.)"}

        lines = [f"Brain: {self._brain_type}",
                 f"Root: {exp_dir}", ""]
        total_chars = 0
        for md in sorted(_collect_memory_files(exp_dir)):
            rel = md.relative_to(exp_dir)
            chars = len(md.read_text(encoding="utf-8", errors="replace"))
            total_chars += chars
            lines.append(f"  {rel} ({chars} chars)")

        lines.append(f"\nTotal: {total_chars} chars across {len(lines)-3} files")
        lines.append("\nTip: Use write_memory(category='topic/subtopic') to organize.")
        lines.append("Large files should be split into categories.")
        return {"ok": True, "output": "\n".join(lines)}


def _collect_memory_files(exp_dir) -> list:
    """Recursively collect all .md files in the experience directory."""
    from pathlib import Path
    all_md = []
    for md in sorted(exp_dir.rglob("*.md")):
        if md.name.startswith("."):
            continue
        all_md.append(md)
    return all_md


def _search_files(files: list, query: str, base_dir) -> list:
    """Keyword search across memory files, returning snippets."""
    query_terms = query.split()
    results = []
    for fpath in files:
        content = fpath.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        rel = fpath.relative_to(base_dir) if str(fpath).startswith(str(base_dir)) \
            else fpath.name
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(t in line_lower for t in query_terms):
                start = max(0, i - 1)
                end = min(len(lines), i + 3)
                snippet = "\n".join(lines[start:end])
                results.append(f"[{rel}:{i+1}] {snippet}")
                if len(results) >= 8:
                    return results
    return results


def should_flush_memory(context_tokens: int, max_tokens: int,
                        reserve: int = 20000, soft_threshold: int = 8000) -> bool:
    """Check if context is near capacity and memory flush should trigger."""
    return context_tokens >= (max_tokens - reserve - soft_threshold)
