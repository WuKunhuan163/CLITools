"""
Agent brain evolution system.

Implements the introspection -> analysis -> suggestion -> application loop
inspired by OpenClaw's V13 Evolution System, adapted for the AITerminalTools
tool-based architecture.

Data files (in tool/SKILLS/data/brain/):
    lessons.jsonl      - Captured lessons from bug fixes and discoveries
    suggestions.jsonl  - Generated improvement suggestions
    evolution.jsonl    - History of applied changes
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

BRAIN_DIR = Path(__file__).resolve().parent.parent.parent.parent / "runtime" / "experience"
LESSONS_FILE = BRAIN_DIR / "lessons.jsonl"
SUGGESTIONS_FILE = BRAIN_DIR / "suggestions.jsonl"
EVOLUTION_FILE = BRAIN_DIR / "evolution.jsonl"


def _read_jsonl(path):
    """Read a JSONL file and return list of parsed entries."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().strip().splitlines():
        try:
            entries.append(json.loads(line))
        except Exception:
            continue
    return entries


def _append_jsonl(path, entry):
    """Append a single entry to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_lesson(lesson, context="", tool_name="", severity="info"):
    """Record a lesson to the brain."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "lesson": lesson,
        "severity": severity,
    }
    if context:
        entry["context"] = context
    if tool_name:
        entry["tool"] = tool_name
    _append_jsonl(LESSONS_FILE, entry)
    return sum(1 for _ in open(LESSONS_FILE))


def get_lessons(last_n=10, tool_filter="", days=None):
    """Retrieve lessons with optional filtering."""
    entries = _read_jsonl(LESSONS_FILE)
    if days is not None:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        entries = [e for e in entries if e.get("timestamp", "") >= cutoff]
    if tool_filter:
        entries = [e for e in entries if e.get("tool", "") == tool_filter]
    return entries[-last_n:] if last_n else entries


def analyze(days=30, tool_filter=""):
    """Analyze lessons for patterns. Returns structured analysis dict."""
    entries = get_lessons(last_n=0, tool_filter=tool_filter, days=days)
    if not entries:
        return None

    by_tool = Counter(e.get("tool", "unknown") for e in entries)
    by_severity = Counter(e.get("severity", "info") for e in entries)

    words = []
    for e in entries:
        words.extend(w for w in e.get("lesson", "").lower().split() if len(w) > 5)
    top_keywords = Counter(words).most_common(10)

    return {
        "total": len(entries),
        "days": days,
        "by_tool": dict(by_tool.most_common()),
        "by_severity": dict(by_severity),
        "recurring_terms": [(w, c) for w, c in top_keywords if c >= 2],
        "most_affected": by_tool.most_common(1)[0] if by_tool else None,
        "critical_count": by_severity.get("critical", 0),
    }


def suggest(focus="all"):
    """Generate improvement suggestions. Returns list of suggestion dicts."""
    entries = _read_jsonl(LESSONS_FILE)
    if not entries:
        return []

    suggestions = []
    by_tool = {}
    critical_lessons = []
    for e in entries:
        t = e.get("tool", "unknown")
        by_tool.setdefault(t, []).append(e)
        if e.get("severity") == "critical":
            critical_lessons.append(e)

    for tool_name, lessons in by_tool.items():
        if tool_name == "unknown":
            continue
        if len(lessons) >= 3:
            suggestions.append({
                "id": f"rule-{tool_name.lower().replace('.', '-')}-{len(suggestions)+1}",
                "type": "rule",
                "tool": tool_name,
                "confidence": min(0.5 + len(lessons) * 0.1, 0.9),
                "content": f"Create a dedicated for_agent.md rule consolidating {len(lessons)} lessons for {tool_name}.",
                "evidence": [e.get("lesson", "")[:80] for e in lessons[:3]],
                "timestamp": datetime.now().isoformat(),
            })

    for e in critical_lessons:
        tool_name = e.get("tool", "unknown")
        suggestions.append({
            "id": f"hook-{tool_name.lower().replace('.', '-')}-{len(suggestions)+1}",
            "type": "hook",
            "tool": tool_name,
            "confidence": 0.8,
            "content": f"Create a pre-commit hook for: {e.get('lesson', '')[:100]}",
            "evidence": [e.get("lesson", ""), e.get("context", "")],
            "timestamp": datetime.now().isoformat(),
        })

    if suggestions:
        SUGGESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SUGGESTIONS_FILE, "w") as f:
            for s in suggestions:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

    return suggestions


def apply_suggestion(suggestion_id):
    """Apply a suggestion by ID. Returns (success, message)."""
    suggestions = _read_jsonl(SUGGESTIONS_FILE)
    target = None
    for s in suggestions:
        if s.get("id") == suggestion_id:
            target = s
            break
    if not target:
        return False, f"Suggestion '{suggestion_id}' not found."

    evolution_entry = {
        "timestamp": datetime.now().isoformat(),
        "suggestion_id": suggestion_id,
        "type": target["type"],
        "tool": target.get("tool", ""),
        "content": target["content"],
        "confidence": target["confidence"],
        "status": "applied",
    }
    _append_jsonl(EVOLUTION_FILE, evolution_entry)
    return True, f"Recorded application of suggestion '{suggestion_id}'."


def get_evolution_history(last_n=20):
    """Get evolution history entries."""
    entries = _read_jsonl(EVOLUTION_FILE)
    return entries[-last_n:]


def introspect(max_transcripts=5):
    """Analyze recent agent transcripts to identify behavior patterns.

    Returns a structured report with tool usage frequency, common error
    patterns, session statistics, and improvement opportunities.
    """
    import re
    project_name = BRAIN_DIR.parent.parent.name
    cursor_projects = Path.home() / ".cursor" / "projects" / f"Applications-{project_name}"
    transcripts_dir = cursor_projects / "agent-transcripts"
    if not transcripts_dir.exists():
        transcripts_dir = BRAIN_DIR.parent.parent / "agent-transcripts"
    if not transcripts_dir.exists():
        return None

    transcript_dirs = sorted(transcripts_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    transcript_dirs = [d for d in transcript_dirs if d.is_dir()][:max_transcripts]

    if not transcript_dirs:
        return None

    tool_mentions = Counter()
    error_patterns = Counter()
    total_messages = 0
    user_messages = 0
    assistant_messages = 0
    Counter()

    tool_names_pattern = re.compile(
        r'\b(WHATSAPP|GMAIL|GOOGLE\.GCS|GOOGLE\.GC|GOOGLE\.GD|GOOGLE\.CDMCP|GOOGLE\.GS|'
        r'GOOGLE|XMIND|WPS|YOUTUBE|BILIBILI|FIGMA|LUCIDCHART|CHARTCUBE|ASANA|ATLASSIAN|'
        r'CLOUDFLARE|INTERCOM|KLING|LINEAR|PAYPAL|SENTRY|SQUARE|TAVILY|PYTHON|FONT|GIT|'
        r'DRAW|FITZ|USERINPUT|VPN|SKILLS|BACKGROUND|MIDJOURNEY|HEYGEN|KIMI|DINGTALK|'
        r'SUNO|ZAPIER|STRIPE|GITLAB|GITHUB|PLAID|BOARDMIX|COGGLE|MIRO|WHIMSICAL|'
        r'OCR|YUQUE|FILEDIALOG|iCloud)\b'
    )

    error_keywords = re.compile(
        r'\b(error|failed|exception|traceback|bug|fix|broken|crash|timeout|'
        r'missing|not found|permission denied|refused|rate limit)\b',
        re.IGNORECASE
    )

    for tdir in transcript_dirs:
        jsonl_files = list(tdir.glob("*.jsonl"))
        if not jsonl_files:
            continue
        for jf in jsonl_files:
            try:
                for line in jf.read_text(errors="ignore").splitlines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    role = obj.get("role", "")
                    total_messages += 1
                    if role == "user":
                        user_messages += 1
                    elif role == "assistant":
                        assistant_messages += 1

                    msg = obj.get("message", {})
                    content = msg.get("content", [])
                    text = ""
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = " ".join(
                            c.get("text", "") for c in content
                            if isinstance(c, dict) and "text" in c
                        )

                    for m in tool_names_pattern.finditer(text):
                        tool_mentions[m.group()] += 1

                    for m in error_keywords.finditer(text):
                        error_patterns[m.group().lower()] += 1
            except Exception:
                continue

    if total_messages == 0:
        return None

    return {
        "transcripts_analyzed": len(transcript_dirs),
        "total_messages": total_messages,
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "tool_mentions": dict(tool_mentions.most_common(15)),
        "error_keywords": dict(error_patterns.most_common(10)),
        "ratio_assistant_to_user": round(assistant_messages / max(user_messages, 1), 1),
        "improvement_opportunities": _derive_opportunities(tool_mentions, error_patterns),
    }


def _derive_opportunities(tool_mentions, error_patterns):
    """Generate improvement opportunities from introspection data."""
    opps = []
    fix_count = error_patterns.get("fix", 0)
    error_count = error_patterns.get("error", 0)
    if fix_count > 5:
        opps.append({
            "type": "quality",
            "message": f"High fix frequency ({fix_count} mentions) suggests recurring issues. "
                       "Review lessons for systematic root causes.",
            "priority": "high",
        })
    if error_count > 10:
        opps.append({
            "type": "robustness",
            "message": f"High error frequency ({error_count} mentions). "
                       "Consider adding pre-flight checks to frequently failing tools.",
            "priority": "high",
        })
    top_tools = tool_mentions.most_common(3)
    for tool, count in top_tools:
        if count > 20:
            opps.append({
                "type": "focus",
                "message": f"{tool} is heavily used ({count} mentions). "
                           "Ensure its for_agent.md is comprehensive and up-to-date.",
                "priority": "medium",
            })
    timeout_count = error_patterns.get("timeout", 0)
    if timeout_count > 3:
        opps.append({
            "type": "performance",
            "message": f"Timeout issues detected ({timeout_count} mentions). "
                       "Review affected tools for slow operations and add timeout handling.",
            "priority": "medium",
        })
    if not opps:
        opps.append({
            "type": "info",
            "message": "No significant patterns detected. Continue recording lessons.",
            "priority": "low",
        })
    return opps
