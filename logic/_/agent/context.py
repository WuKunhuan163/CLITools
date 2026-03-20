"""Agent context builder — constructs the context fed to the LLM.

Three tiers of context richness:
  Tier 0 (Minimal):  Command output only. For AI IDEs with their own context.
  Tier 1 (Standard): Output + directory listing + error hints + tool discovery.
  Tier 2 (Full):     Everything + skills injection + quality checks + nudges.
"""
import datetime
import os
import platform
import re
from typing import Any, Dict, List, Optional, Set

from logic._.agent.state import AgentSession


def _extract_keywords(text: str, min_len: int = 3) -> Set[str]:
    """Extract lowercase alpha-numeric keywords from text."""
    tokens = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text.lower())
    return {t for t in tokens if len(t) >= min_len}


_GENERIC_WORDS = frozenset([
    "the", "and", "for", "that", "this", "with", "from", "have",
    "are", "was", "were", "but", "not", "you", "all", "can",
    "had", "her", "one", "our", "out", "day", "get", "has", "him",
    "his", "how", "its", "let", "may", "new", "now", "old", "see",
    "way", "who", "did", "set", "use", "will", "help", "please",
    "make", "create", "build", "write", "add", "fix", "run",
    "code", "file", "project", "tool", "want", "need", "like",
])


def _is_related_prompt(original: str, current: str,
                       threshold: float = 0.15) -> bool:
    """Check whether current prompt is topically related to the original.

    Uses keyword overlap ratio. Returns False when the new prompt
    shares very few meaningful words with the original task, suggesting
    the user has moved on to a completely different topic.
    """
    if not original or not current:
        return True
    orig_kw = _extract_keywords(original) - _GENERIC_WORDS
    curr_kw = _extract_keywords(current) - _GENERIC_WORDS
    if not orig_kw or not curr_kw:
        return True
    overlap = len(orig_kw & curr_kw)
    denom = min(len(orig_kw), len(curr_kw))
    return (overlap / denom) >= threshold if denom > 0 else True


def build_runtime_header(codebase_root: str) -> str:
    """Build a runtime state header."""
    return "\n".join([
        "---",
        f"timestamp: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"platform: {platform.system()} {platform.release()}",
        f"cwd: {codebase_root}",
        "---",
    ])


def build_directory_listing(cwd: str, limit: int = 30) -> str:
    """List files in the working directory."""
    try:
        files = [f for f in os.listdir(cwd) if not f.startswith('.')]
        if files:
            listing = ", ".join(sorted(files)[:limit])
            return f"[Files in directory] {listing}"
        return "[Files in directory] (empty)"
    except OSError:
        return ""


REMINDER_SCHEDULE = {
    "tool_ecosystem": 3,
    "memory_refresh": 5,
    "quality_guidelines": 5,
}


def _build_tool_ecosystem_reminder() -> str:
    """Periodic reminder of the tool ecosystem."""
    return (
        "[Ecosystem reminder] "
        "This project uses AITerminalTools. Tool name = command (GIT, PYTHON, etc.). "
        "Discover tools: exec 'TOOL --search tools \"keyword\"'. "
        "Load skills: exec 'SKILLS show <name>'. "
        "Read docs: read_file('tool/<NAME>/for_agent.md')."
    )


def _build_quality_reminder() -> str:
    """Periodic quality guidelines reminder."""
    return (
        "[Quality reminder] "
        "After writing/editing, verify with read_file. "
        "Use edit_file for targeted changes (not full rewrite). "
        "If stuck after 3 failed attempts, try a different strategy or ask_user."
    )


def build_context(session: AgentSession, user_text: str,
                  tier: int = 1,
                  context_feed: Optional[Dict[str, Any]] = None,
                  project_root: str = "") -> str:
    """Package user text with system context for the LLM.

    Context is tiered by richness:
      Tier 0: Command output only (for AI IDEs with their own context).
      Tier 1: + directory listing + error hints + tool discovery.
      Tier 2: + skills injection + quality checks + periodic reminders.

    Reminder schedule for feed rounds (message_count > 1):
      Every feed:    runtime header, environment, original task, read-before-write
      Every 3 feeds: tool ecosystem reminder
      Every 5 feeds: memory refresh, quality guidelines
      First only:    full soul + bootstrap context
    """
    parts = []
    cwd = session.codebase_root
    msg_num = session.message_count

    if tier >= 2 and msg_num <= 1 and project_root:
        try:
            from logic._.agent.brain import inject_bootstrap_context
            brain_type = getattr(session, "brain_type", "default") or "default"
            bootstrap = inject_bootstrap_context(project_root, brain_type)
            if bootstrap.strip():
                parts.append(bootstrap)
        except Exception:
            pass

    if tier >= 1 and msg_num <= 1:
        parts.append(build_runtime_header(cwd))
        parts.append(
            f"[Working directory] {cwd}\n"
            f"All relative paths resolve against this directory.")
        listing = build_directory_listing(cwd)
        if listing:
            parts.append(listing)

    if tier >= 1 and msg_num > 1:
        parts.append(build_runtime_header(cwd))
        original_prompt = getattr(session, "initial_prompt", "")
        if original_prompt and _is_related_prompt(original_prompt, user_text):
            summary = original_prompt[:300]
            parts.append(f"[Original task] {summary}")
        elif original_prompt:
            parts.append(
                "[New topic] The user's message appears unrelated to the "
                "previous task. Treat it as a fresh request.")
        listing = build_directory_listing(cwd, limit=20)
        if listing:
            parts.append(
                f"[IMPORTANT] Before modifying any file, you MUST "
                f"read_file first. Use absolute paths when the task "
                f"references files outside your working directory. {listing}")

    if tier >= 2 and msg_num > 1:
        if msg_num % REMINDER_SCHEDULE["tool_ecosystem"] == 0:
            parts.append(_build_tool_ecosystem_reminder())

        if msg_num % REMINDER_SCHEDULE["memory_refresh"] == 0 and project_root:
            try:
                from logic._.agent.brain import inject_memory_only
                memory_block = inject_memory_only(project_root,
                    getattr(session, "brain_type", "default") or "default")
                if memory_block.strip():
                    parts.append(f"[Memory refresh]\n{memory_block}")
            except (ImportError, Exception):
                pass

        if msg_num % REMINDER_SCHEDULE["quality_guidelines"] == 0:
            parts.append(_build_quality_reminder())

    if tier >= 1:
        env_block = session.environment.serialize()
        if env_block:
            parts.append(env_block)

    if context_feed:
        feed_parts = []
        if context_feed.get("hint"):
            feed_parts.append(f"[System hint] {context_feed['hint']}")
        if context_feed.get("errors"):
            feed_parts.append("[Known errors]\n" +
                              "\n".join(f"  - {e}" for e in context_feed["errors"]))
        if context_feed.get("tools_available"):
            lines = ["[Available tools]"]
            for name, desc in context_feed["tools_available"].items():
                lines.append(f"  {name}: {desc}")
            feed_parts.append("\n".join(lines))
        if feed_parts:
            parts.append("\n".join(feed_parts))

    parts.append(user_text)
    return "\n\n".join(parts)
