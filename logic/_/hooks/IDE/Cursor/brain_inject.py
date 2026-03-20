#!/usr/bin/env python3
"""sessionStart hook: Inject brain + ecosystem context into Cursor agent.

Fires once when a new Cursor conversation begins. Injects:
1. Brain state (tasks.json, context.md) from data/_/runtime/_/eco/brain/
2. Ecosystem context (skill catalog, exploration guide, agent behaviors)
3. Recent experience lessons from data/_/runtime/_/eco/experience/lessons.jsonl

This gives the Cursor agent the same context-awareness as the LLM tool's agent.
"""
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime

LOG_FILE = Path("/tmp/cursor-hooks.log")


def _log(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] brain_inject: {msg}\n")
    except Exception:
        pass


def _load_brain(project_dir: Path) -> list:
    parts = []
    brain_dir = project_dir / "data" / "_" / "runtime" / "_" / "eco" / "brain"

    tasks_file = brain_dir / "tasks.json"
    if tasks_file.exists():
        try:
            data = json.loads(tasks_file.read_text())
            active = [t for t in data.get("tasks", []) if t.get("status") != "done"]
            if active:
                lines = [f"  #{t['id']} [{t['status']}] {t['content']}" for t in active[:15]]
                parts.append("## Active Tasks\n" + "\n".join(lines))
        except Exception:
            pass

    context_file = brain_dir / "context.md"
    if context_file.exists():
        content = context_file.read_text().strip()
        if content and "not yet initialized" not in content:
            parts.append(f"## Context\n{content}")

    return parts


def _load_lessons(project_dir: Path, count: int = 5) -> list:
    parts = []
    experience_file = project_dir / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl"
    if experience_file.exists():
        lines = experience_file.read_text().strip().split("\n")
        recent = lines[-count:] if len(lines) > count else lines
        lessons = []
        for line in recent:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                lessons.append(f"- [{obj.get('severity', 'info')}] {obj.get('lesson', '')[:120]}")
            except json.JSONDecodeError:
                pass
        if lessons:
            parts.append("## Recent Lessons\n" + "\n".join(lessons))

    return parts


def _load_ecosystem(project_dir: Path) -> list:
    parts = []
    sys.path.insert(0, str(project_dir))
    try:
        from logic._.agent.ecosystem import build_ecosystem_info
        eco = build_ecosystem_info(str(project_dir))

        if eco.get("guidelines"):
            parts.append(f"## Guidelines\n{eco['guidelines']}")
        if eco.get("skill_catalog"):
            catalog_str = "\n".join(f"- {s}" for s in eco["skill_catalog"][:15])
            parts.append(f"## Available Skills\n{catalog_str}\nLoad: exec 'SKILLS show <name>'")
        if eco.get("agent_behaviors"):
            behaviors = "\n".join(f"- {b}" for b in eco["agent_behaviors"])
            parts.append(f"## Agent Behaviors\n{behaviors}")
        if eco.get("exploration"):
            parts.append(f"## Exploration\n{eco['exploration']}")
    except Exception as e:
        _log(f"ecosystem load error: {e}")
    finally:
        if str(project_dir) in sys.path:
            sys.path.remove(str(project_dir))

    return parts


def _load_reflection(project_dir: Path) -> list:
    """Load system gaps from brain tasks for agent awareness."""
    parts = []
    tasks_file = project_dir / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "tasks.md"
    if False and tasks_file.exists():  # Disabled: gaps are now in brain tasks, loaded via context
        content = tasks_file.read_text(encoding="utf-8")
        for section_header in ("## Current System Gaps", "## Known Gaps"):
            if section_header in content:
                start = content.index(section_header)
                rest = content[start + len(section_header):]
                end = rest.find("\n## ")
                if end < 0:
                    end = len(rest)
                gaps_text = rest[:end].strip()
                gap_lines = []
                for line in gaps_text.split("\n"):
                    if line.startswith("**Gap:") or line.startswith("### Gap"):
                        cleaned = line.lstrip("#* ").rstrip("*").strip()
                        if cleaned.startswith("Gap:"):
                            cleaned = cleaned[4:].strip()
                        em_end = cleaned.find("**")
                        if em_end > 0:
                            cleaned = cleaned[:em_end].strip()
                        dash = cleaned.find("—")
                        if dash > 0:
                            cleaned = cleaned[:dash].strip()
                        gap_lines.append(cleaned)
                if gap_lines:
                    parts.append("## Known System Gaps\n" +
                                 "\n".join(f"- {g}" for g in gap_lines))
                break
    return parts


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        _log(f"ERROR parsing stdin: {e}")
        print(json.dumps({}))
        return

    workspace_roots = payload.get("workspace_roots", [])
    project_dir = Path(workspace_roots[0]) if workspace_roots else Path("/Applications/AITerminalTools")
    _log(f"project_dir={project_dir}")

    parts = []
    parts.extend(_load_brain(project_dir))
    parts.extend(_load_lessons(project_dir))
    parts.extend(_load_ecosystem(project_dir))
    parts.extend(_load_reflection(project_dir))

    cursor_userinput_rule = ""

    try:
        sys.path.insert(0, str(project_dir))
        from logic._.setup.ide_detect import detect_all
        detected_ides = detect_all(project_dir)
    except Exception:
        detected_ides = ["cursor"]
    ide_str = ", ".join(detected_ides) if detected_ides else "unknown"

    cli_primer = (
        f"Environment: {ide_str} IDE detected. "
        "Tools are CLI commands — run them in the terminal shell, not as Python imports. "
        "Symmetric design: tool/<NAME>/ each has main.py, logic/, interface/, tool.json. "
        "Root mirrors this: logic/ (shared), interface/ (facade, import from here), bin/ (executables), data/ (API keys/caches, gitignored), tmp/ (temp scripts, gitignored). "
        "Every directory has README.md (users) + AGENT.md (agents) — read these for context. "
        "Run `TOOL status` to see installed tools. "
        "Run `TOOL --search all \"query\"` to find anything. "
        "Read AGENT.md Section 0 for the bootstrap protocol, then start working.\n\n"
    )

    metacog_primer = (
        "\n\n## METACOGNITIVE DEVELOPMENT (always active)\n"
        "Beyond completing the task, you have two standing responsibilities:\n"
        "1. **Self-Iteration**: Get faster each round. If you re-derive something, fix the discovery path.\n"
        "2. **Environment Improvement**: Fix nearby problems (docs, tests, inconsistencies) proactively.\n"
        "After each task: verify results are user-visible, scan for nearby issues, "
        "take a proactive quality pass (see skills/_/meta-agent 'Proactive Quality Pass'), "
        "record improvements via BRAIN log.\n"
    )

    output = {}
    if parts:
        output["additional_context"] = (
            "--- AGENT BRAIN + ECOSYSTEM ---\n"
            + cli_primer
            + "\n\n".join(parts)
            + metacog_primer
            + "\n--- END ---\n"
            "Read tasks above and continue where you left off. "
            "Update brain: `python3 bin/BRAIN add/done/list` to manage tasks."
            + cursor_userinput_rule
        )
    else:
        output["additional_context"] = (
            cli_primer
            + "Agent brain is empty. When the user gives you tasks, "
            "run `python3 bin/BRAIN add \"<task>\"` immediately to record them."
            + metacog_primer
            + cursor_userinput_rule
        )

    result = json.dumps(output)
    _log(f"injected {len(result)} chars, {len(parts)} sections")
    print(result)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
