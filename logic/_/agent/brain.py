"""Brain type management — personality and context injection.

A "brain" is a named collection of bootstrap files that define an agent's
personality, expertise, memory, and user context. Brain types are stored in:

    experience/<brain_type>/
        SOUL.md        — Agent personality, communication style, values
        IDENTITY.md    — Agent name, role, goals
        USER.md        — User preferences
        MEMORY.md      — Long-term persistent facts
        daily/         — Daily working logs (YYYY-MM-DD.md)

The default brain type is "default". Tools can specify a custom brain type
to give their agents specialized personalities.
"""
import os
from pathlib import Path
from typing import Dict, Optional

MAX_FILE_CHARS = 20000
MAX_TOTAL_CHARS = 100000

BOOTSTRAP_FILES = ["SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md"]


def get_experience_dir(project_root: str, brain_type: str = "default") -> Path:
    """Return the experience directory for a given brain type."""
    return Path(project_root) / "data" / "_" / "runtime" / "_" / "eco" / "experience" / brain_type


def ensure_experience_dir(project_root: str, brain_type: str = "default") -> Path:
    """Create the experience directory and seed with templates if needed."""
    d = get_experience_dir(project_root, brain_type)
    d.mkdir(parents=True, exist_ok=True)
    (d / "daily").mkdir(exist_ok=True)

    if not (d / "SOUL.md").exists():
        (d / "SOUL.md").write_text(_DEFAULT_SOUL)
    if not (d / "MEMORY.md").exists():
        (d / "MEMORY.md").write_text("# Memory\n\nNo persistent facts recorded yet.\n")
    return d


def load_bootstrap(project_root: str, brain_type: str = "default") -> Dict[str, str]:
    """Load bootstrap files from the experience directory.

    Returns a dict of {filename: content} with truncation applied.
    """
    d = get_experience_dir(project_root, brain_type)
    if not d.exists():
        return {}

    result = {}
    total = 0
    for fname in BOOTSTRAP_FILES:
        fpath = d / fname
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8", errors="replace")
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n\n[...truncated...]"
        if total + len(content) > MAX_TOTAL_CHARS:
            break
        result[fname] = content
        total += len(content)
    return result


def load_recent_daily(project_root: str, brain_type: str = "default",
                      days: int = 2) -> Dict[str, str]:
    """Load the most recent daily notes."""
    import datetime
    d = get_experience_dir(project_root, brain_type) / "daily"
    if not d.exists():
        return {}

    result = {}
    today = datetime.date.today()
    for i in range(days):
        date = today - datetime.timedelta(days=i)
        fname = f"{date.isoformat()}.md"
        fpath = d / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8", errors="replace")
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + "\n\n[...truncated...]"
            result[fname] = content
    return result


def inject_memory_only(project_root: str, brain_type: str = "default") -> str:
    """Load just the MEMORY.md file for periodic refresh during feed rounds."""
    d = get_experience_dir(project_root, brain_type)
    fpath = d / "MEMORY.md"
    if fpath.exists():
        content = fpath.read_text(encoding="utf-8", errors="replace")
        return content[:MAX_FILE_CHARS]
    return ""


def inject_bootstrap_context(project_root: str, brain_type: str = "default") -> str:
    """Build the injected context block from bootstrap + recent daily notes."""
    parts = []
    bootstrap = load_bootstrap(project_root, brain_type)
    daily = load_recent_daily(project_root, brain_type)

    if bootstrap or daily:
        parts.append("## Project Context\n")

    for fname, content in bootstrap.items():
        label = fname.replace(".md", "")
        parts.append(f"### {label}\n{content}\n")

    for fname, content in daily.items():
        parts.append(f"### Daily Note: {fname}\n{content}\n")

    return "\n".join(parts)


def write_daily_note(project_root: str, content: str,
                     brain_type: str = "default"):
    """Append content to today's daily note."""
    import datetime
    d = ensure_experience_dir(project_root, brain_type) / "daily"
    today = datetime.date.today().isoformat()
    fpath = d / f"{today}.md"

    if fpath.exists():
        existing = fpath.read_text(encoding="utf-8", errors="replace")
        fpath.write_text(existing + "\n" + content, encoding="utf-8")
    else:
        fpath.write_text(f"# Daily Note: {today}\n\n{content}\n", encoding="utf-8")


def write_memory(project_root: str, content: str,
                 brain_type: str = "default", category: str = ""):
    """Append a fact to MEMORY.md, optionally within a category subdirectory."""
    d = ensure_experience_dir(project_root, brain_type)
    if category:
        cat_dir = d / category.strip("/")
        cat_dir.mkdir(parents=True, exist_ok=True)
        fpath = cat_dir / "MEMORY.md"
    else:
        fpath = d / "MEMORY.md"
    existing = fpath.read_text(encoding="utf-8", errors="replace") if fpath.exists() else ""
    fpath.write_text(existing + "\n" + content + "\n", encoding="utf-8")


def list_brain_types(project_root: str):
    """List available brain types."""
    exp_dir = Path(project_root) / "data" / "_" / "runtime" / "_" / "eco" / "experience"
    if not exp_dir.exists():
        return []
    return sorted(
        d.name for d in exp_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


_DEFAULT_SOUL = """# Soul

## Personality
- Direct and action-oriented. Lead with answers, not preambles.
- Methodical. Break complex tasks into clear steps.
- Honest about limitations. Say "I don't know" rather than guess.

## Communication Style
- Default to short responses (2-4 sentences) unless depth is needed.
- Use bullet points for lists.
- No filler phrases ("Great question!", "I'd be happy to help").
- Show code/commands, not just descriptions.

## Values
- Accuracy over speed.
- Working code over theoretical explanations.
- Read before writing. Verify after changing.

## Expertise
- Software development (Python, web, CLI tools)
- System administration and shell scripting
- Code review and debugging

## Anti-Patterns
- Never apologize for previous responses — just improve.
- Never summarize user's question back as preamble.
- Never suggest "consult a professional" for technical questions.
"""
