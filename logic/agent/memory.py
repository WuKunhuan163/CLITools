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
            "description": "Write a permanent fact to MEMORY.md (persists across sessions).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string",
                                "description": "The fact or knowledge to persist"},
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
            "description": "Search memory files for relevant knowledge.",
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
]


class MemoryHandlers:
    """Tool handlers for memory operations."""

    def __init__(self, project_root: str, brain_type: str = "default"):
        self._project_root = project_root
        self._brain_type = brain_type

    def handle_write_memory(self, args: dict) -> dict:
        content = args.get("content", "")
        if not content:
            return {"ok": False, "output": "No content provided."}
        write_memory(self._project_root, content, self._brain_type)
        return {"ok": True, "output": f"Written to MEMORY.md ({len(content)} chars)."}

    def handle_write_daily(self, args: dict) -> dict:
        content = args.get("content", "")
        if not content:
            return {"ok": False, "output": "No content provided."}
        write_daily_note(self._project_root, content, self._brain_type)
        today = datetime.date.today().isoformat()
        return {"ok": True, "output": f"Appended to daily/{today}.md ({len(content)} chars)."}

    def handle_recall_memory(self, args: dict) -> dict:
        """Simple keyword search over memory files (TF-IDF fallback)."""
        query = args.get("query", "").lower()
        if not query:
            return {"ok": False, "output": "No query provided."}

        results = []
        exp_dir = get_experience_dir(self._project_root, self._brain_type)
        if not exp_dir.exists():
            return {"ok": True, "output": "(No memory files found.)"}

        search_files = []
        memory_path = exp_dir / "MEMORY.md"
        if memory_path.exists():
            search_files.append(memory_path)
        daily_dir = exp_dir / "daily"
        if daily_dir.exists():
            search_files.extend(sorted(daily_dir.glob("*.md"), reverse=True)[:7])

        for fpath in search_files:
            content = fpath.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if query in line.lower():
                    start = max(0, i - 1)
                    end = min(len(lines), i + 3)
                    snippet = "\n".join(lines[start:end])
                    results.append(f"[{fpath.name}:{i+1}] {snippet}")
                    if len(results) >= 5:
                        break
            if len(results) >= 5:
                break

        if not results:
            return {"ok": True, "output": f"No matches for '{query}' in memory files."}
        return {"ok": True, "output": "\n---\n".join(results)}


def should_flush_memory(context_tokens: int, max_tokens: int,
                        reserve: int = 20000, soft_threshold: int = 8000) -> bool:
    """Check if context is near capacity and memory flush should trigger."""
    return context_tokens >= (max_tokens - reserve - soft_threshold)
