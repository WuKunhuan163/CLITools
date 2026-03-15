"""Agent context builder — constructs the context fed to the LLM.

Three tiers of context richness:
  Tier 0 (Minimal):  Command output only. For AI IDEs with their own context.
  Tier 1 (Standard): Output + directory listing + error hints + tool discovery.
  Tier 2 (Full):     Everything + skills injection + quality checks + nudges.
"""
import datetime
import os
import platform
from typing import Any, Dict, List, Optional

from logic.agent.state import AgentSession


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


def build_context(session: AgentSession, user_text: str,
                  tier: int = 1,
                  context_feed: Optional[Dict[str, Any]] = None,
                  project_root: str = "") -> str:
    """Package user text with system context for the LLM.

    Args:
        session: Current agent session.
        user_text: The user's message.
        tier: Context richness (0=minimal, 1=standard, 2=full).
        context_feed: Additional context hints.
        project_root: Project root for brain/experience file loading.

    Returns:
        Packaged message string.
    """
    parts = []
    cwd = session.codebase_root

    if tier >= 2 and session.message_count <= 1 and project_root:
        try:
            from logic.agent.brain import inject_bootstrap_context
            brain_type = getattr(session, "brain_type", "default") or "default"
            bootstrap = inject_bootstrap_context(project_root, brain_type)
            if bootstrap.strip():
                parts.append(bootstrap)
        except Exception:
            pass

    if tier >= 1 and session.message_count <= 1:
        parts.append(build_runtime_header(cwd))
        parts.append(
            f"[Working directory] {cwd}\n"
            f"All relative paths resolve against this directory.")
        listing = build_directory_listing(cwd)
        if listing:
            parts.append(listing)

    if tier >= 1 and session.message_count > 1:
        listing = build_directory_listing(cwd, limit=20)
        if listing:
            parts.append(
                f"[IMPORTANT] Before modifying any file, you MUST "
                f"read_file first. {listing}")

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
