#!/usr/bin/env python3 -u
import sys
import os
import argparse
from pathlib import Path

def find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root:
    root_str = str(project_root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
else:
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

from logic.tool.blueprint.base import ToolBase
from interface.config import get_color

CURSOR_SKILLS_DIR = Path.home() / ".cursor" / "skills"
LIBRARY_DIR = Path(__file__).resolve().parent / "logic" / "library"
PROJECT_SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"
BRAIN_DIR = Path(__file__).resolve().parent.parent.parent / "runtime" / "experience"
LESSONS_FILE = BRAIN_DIR / "lessons.jsonl"


def _collect_skills_from(directory):
    """Return list of (name, path, description) for all skills in a directory (recursive)."""
    skills = []
    if not directory.exists():
        return skills
    for skill_file in sorted(directory.rglob("SKILL.md")):
        skill_dir = skill_file.parent
        desc = _parse_description(skill_file)
        rel = skill_dir.relative_to(directory)
        skills.append((skill_dir.name, rel, desc, skill_dir))
    return skills


def get_skills():
    """Return list of (name, rel_path, description, abs_path) for all skills."""
    skills = _collect_skills_from(LIBRARY_DIR)
    skills.extend(_collect_skills_from(PROJECT_SKILLS_DIR))
    return sorted(skills, key=lambda x: x[0])


def _parse_description(skill_file: Path) -> str:
    """Extract description from SKILL.md YAML frontmatter."""
    in_frontmatter = False
    for line in skill_file.read_text().splitlines():
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter and line.startswith("description:"):
            return line[len("description:"):].strip()
    return ""


def _find_skill(name):
    """Find a skill by name across all sources. Returns path or None."""
    for search_dir in [LIBRARY_DIR, PROJECT_SKILLS_DIR]:
        if not search_dir.exists():
            continue
        for skill_file in search_dir.rglob("SKILL.md"):
            if skill_file.parent.name == name:
                return skill_file
    return None


def sync_skills():
    """Create symlinks from ~/.cursor/skills/ to project skills only.

    Library skills (100 general CS topics) are NOT synced to Cursor
    to avoid excessive context. Use 'SKILLS show <name>' to read them.
    """
    CURSOR_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    synced = 0
    if not PROJECT_SKILLS_DIR.exists():
        return synced
    for skill_file in PROJECT_SKILLS_DIR.rglob("SKILL.md"):
        skill_dir = skill_file.parent
        target = CURSOR_SKILLS_DIR / skill_dir.name
        if target.is_symlink():
            if target.resolve() == skill_dir.resolve():
                synced += 1
                continue
            target.unlink()
        elif target.exists():
            continue
        target.symlink_to(skill_dir)
        synced += 1
    return synced


def _record_lesson(lesson, context, tool_name, severity, BOLD, GREEN, RESET):
    """Append a lesson to the brain's JSONL log."""
    from tool.SKILLS.logic.evolution import record_lesson
    count = record_lesson(lesson, context, tool_name, severity)
    print(f"  {BOLD}{GREEN}Recorded{RESET} lesson #{count}: {lesson}")
    if severity == "critical":
        print(f"  Consider adding a pre-commit hook to enforce this.")


def _show_lessons(last_n, tool_filter, BOLD, GREEN, RED, RESET):
    """Display recent lessons from the brain log."""
    from tool.SKILLS.logic.evolution import get_lessons
    entries = get_lessons(last_n=last_n, tool_filter=tool_filter)
    if not entries:
        msg = f"  No lessons found" + (f" for tool '{tool_filter}'" if tool_filter else "") + "."
        if not LESSONS_FILE.exists():
            msg = f"  No lessons recorded yet. Use 'SKILLS learn \"...\"' to start."
        print(msg)
        return
    sev_colors = {"info": "", "warning": "\033[33m", "critical": "\033[31m"}
    for e in entries:
        ts = e.get("timestamp", "?")[:16]
        sev = e.get("severity", "info")
        color = sev_colors.get(sev, "")
        reset = "\033[0m" if color else ""
        tool = f" [{e['tool']}]" if e.get("tool") else ""
        print(f"  {BOLD}{ts}{RESET}{tool} {color}[{sev}]{reset} {e.get('lesson', '?')}")
        if e.get("context"):
            print(f"    Context: {e['context']}")


def _analyze_lessons(days, tool_filter, BOLD, GREEN, RED, YELLOW, RESET):
    """Display pattern analysis from the brain's lesson log."""
    from tool.SKILLS.logic.evolution import analyze
    result = analyze(days=days, tool_filter=tool_filter)
    if not result:
        print(f"  No lessons found in the last {days} days.")
        return

    print(f"  {BOLD}Analysis{RESET} ({result['total']} lessons, last {result['days']} days)")
    print()
    print(f"  {BOLD}By Tool:{RESET}")
    for t, c in sorted(result["by_tool"].items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")
    print()
    print(f"  {BOLD}By Severity:{RESET}")
    sev_colors = {"info": "", "warning": YELLOW, "critical": RED}
    for sev in ["critical", "warning", "info"]:
        c = result["by_severity"].get(sev, 0)
        if c > 0:
            color = sev_colors.get(sev, "")
            print(f"    {color}{sev}{RESET}: {c}")
    print()
    if result["recurring_terms"]:
        print(f"  {BOLD}Recurring Terms:{RESET}")
        for word, c in result["recurring_terms"]:
            print(f"    {word}: {c}x")
        print()
    if result["critical_count"] > 0:
        print(f"  {BOLD}{RED}Action Required{RESET}: {result['critical_count']} critical lesson(s) -- consider creating enforcement hooks.")
    if result["most_affected"]:
        name, count = result["most_affected"]
        if count >= 3:
            print(f"  {BOLD}Most Affected Tool{RESET}: {name} ({count} lessons)")
            print(f"  Consider creating a dedicated skill or rule for {name}.")


def _suggest_improvements(focus, BOLD, GREEN, RED, YELLOW, RESET):
    """Display generated improvement suggestions from the brain."""
    from tool.SKILLS.logic.evolution import suggest
    suggestions = suggest(focus=focus)
    if not suggestions:
        print(f"  No suggestions generated. Need more lessons for pattern detection.")
        return
    print(f"  {BOLD}Generated{RESET} {len(suggestions)} suggestion(s):")
    print()
    for s in suggestions:
        conf = s["confidence"]
        conf_color = GREEN if conf >= 0.7 else YELLOW
        print(f"  [{s['id']}] {BOLD}{s['type']}{RESET} (confidence: {conf_color}{conf:.0%}{RESET})")
        print(f"    {s['content']}")
        if s.get("evidence"):
            print(f"    Evidence: {s['evidence'][0][:80]}...")
        print()


def _apply_suggestion(suggestion_id, BOLD, GREEN, RED, YELLOW, RESET):
    """Apply a suggestion with human confirmation."""
    from tool.SKILLS.logic.evolution import apply_suggestion, SUGGESTIONS_FILE, _read_jsonl
    suggestions = _read_jsonl(SUGGESTIONS_FILE)
    target = None
    for s in suggestions:
        if s.get("id") == suggestion_id:
            target = s
            break
    if not target:
        print(f"  {BOLD}{RED}Error{RESET}: Suggestion '{suggestion_id}' not found.")
        print(f"  Run 'SKILLS suggest' first to generate suggestions.")
        return

    print(f"  {BOLD}Suggestion{RESET}: [{target['id']}]")
    print(f"  Type:       {target['type']}")
    print(f"  Tool:       {target.get('tool', 'N/A')}")
    print(f"  Confidence: {target['confidence']:.0%}")
    print(f"  Content:    {target['content']}")
    if target.get("evidence"):
        print(f"  Evidence:")
        for ev in target["evidence"][:3]:
            if ev:
                print(f"    - {ev[:120]}")
    print()

    action_guide = _get_action_guide(target)
    if action_guide:
        print(f"  {BOLD}{GREEN}Action Guide{RESET}:")
        for line in action_guide:
            print(f"    {line}")
        print()

    ok, msg = apply_suggestion(suggestion_id)
    if ok:
        print(f"  {BOLD}{GREEN}Applied{RESET}: {msg}")
    else:
        print(f"  {BOLD}{RED}Failed{RESET}: {msg}")


def _get_action_guide(suggestion):
    """Generate concrete action steps for a suggestion type."""
    stype = suggestion.get("type", "")
    tool = suggestion.get("tool", "unknown")
    if stype == "rule":
        return [
            f"1. Check if tool/{tool}/for_agent.md exists; create if not.",
            f"2. Add a section consolidating lessons from SKILLS lessons --tool {tool}",
            f"3. Include concrete do/don't examples from the evidence.",
            f"4. Run 'SKILLS learn' to mark this pattern as addressed.",
        ]
    elif stype == "hook":
        return [
            f"1. Create tool/{tool}/hooks/pre_commit.py if it doesn't exist.",
            f"2. Implement a check function that detects the anti-pattern.",
            f"3. Register the hook in tool/{tool}/tool.json under 'hooks'.",
            f"4. Test with a deliberate violation to confirm it blocks commits.",
        ]
    elif stype == "skill":
        return [
            f"1. Run 'TOOL --dev create-skill {tool}-patterns'",
            f"2. Document the recurring patterns identified in the evidence.",
            f"3. Include code examples and anti-patterns.",
            f"4. Run 'SKILLS sync' to make it available in Cursor.",
        ]
    return None


def _handle_market(args, BOLD, GREEN, RED, YELLOW, BLUE, RESET):
    """Dispatch marketplace subcommands.

    CLI structure: SKILLS market <source> <action> [args]
    e.g.: SKILLS market clawhub browse
          SKILLS market clawhub search "cursor"
          SKILLS market clawhub install tavily-search
          SKILLS market sources
          SKILLS market installed
    """
    from tool.SKILLS.logic.marketplace import (
        list_sources, browse, install_skill,
        uninstall_skill, list_installed_marketplace_skills,
    )

    ms = args.market_source

    if ms == "sources":
        sources = list_sources()
        print(f"  {BOLD}Marketplace Sources{RESET}:")
        print()
        for s in sources:
            print(f"  {BOLD}{s['id']}{RESET} — {s['name']}")
            print(f"    {s['description']}")
        print()
        print(f"  Usage: SKILLS market <source> <browse|search|install|uninstall>")
        return

    if ms == "installed":
        installed = list_installed_marketplace_skills()
        if not installed:
            print(f"  No marketplace skills installed.")
            print(f"  Browse with: SKILLS market clawhub browse")
            return
        print(f"  {BOLD}Installed Marketplace Skills{RESET} ({len(installed)}):")
        print()
        for s in installed:
            print(f"  {BOLD}{s['slug']}{RESET} (source: {s['source']})")
            print(f"    {s['path']}")
        return

    source_id = ms
    action = getattr(args, "market_action", None)

    if action == "browse":
        print(f"  {BOLD}Fetching skills{RESET} from {source_id}...")
        skills = browse(source_id=source_id, limit=args.limit, category=args.category)
        if not skills:
            print(f"  {RED}No skills found{RESET} or source unavailable.")
            return
        print(f"  {BOLD}Top Skills{RESET} ({source_id}, {args.category}):")
        print()
        for i, s in enumerate(skills, 1):
            cert = f" {GREEN}[certified]{RESET}" if s.get("certified") else ""
            dl = f" ({s['downloads']} dl)" if s.get("downloads") else ""
            print(f"  {BOLD}{i:>3}.{RESET} {s['slug']}{cert}{dl}")
            if s.get("description"):
                print(f"       {s['description'][:90]}")
        print()
        print(f"  Install with: SKILLS market {source_id} install <slug>")
        return

    if action == "search":
        print(f"  {BOLD}Searching{RESET} '{args.query}' on {source_id}...")
        skills = browse(source_id=source_id, query=args.query, limit=args.limit)
        if not skills:
            print(f"  No results for '{args.query}'.")
            return
        print(f"  {BOLD}Search Results{RESET} ({len(skills)} found):")
        print()
        for i, s in enumerate(skills, 1):
            cert = f" {GREEN}[certified]{RESET}" if s.get("certified") else ""
            dl = f" ({s['downloads']} dl)" if s.get("downloads") else ""
            print(f"  {BOLD}{i:>3}.{RESET} {s['slug']}{cert}{dl}")
            if s.get("description"):
                print(f"       {s['description'][:90]}")
        return

    if action == "install":
        print(f"  {BOLD}Installing{RESET} '{args.slug}' from {source_id}...")
        ok, msg, path = install_skill(source_id, args.slug)
        if ok:
            print(f"  {BOLD}{GREEN}Installed{RESET}: {msg}")
            print(f"  Saved to: {path}")
            print(f"  Run 'SKILLS sync' to make it available in Cursor.")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {msg}")
        return

    if action == "uninstall":
        ok, msg = uninstall_skill(source_id, args.slug)
        if ok:
            print(f"  {BOLD}{GREEN}Removed{RESET}: {msg}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {msg}")
        return

    print(f"  Usage: SKILLS market {source_id} <browse|search|install|uninstall>")


def main():
    tool = ToolBase("SKILLS")

    parser = argparse.ArgumentParser(description="Manage AI Agent Skills", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    subparsers.add_parser("list", help="List all available skills")
    show_p = subparsers.add_parser("show", help="Show a skill's content")
    show_p.add_argument("name", help="Skill name")
    subparsers.add_parser("sync", help="Sync skills to Cursor's skills directory")
    subparsers.add_parser("path", help="Show skills library path")

    search_p = subparsers.add_parser("search", help="Semantic search for skills")
    search_p.add_argument("query", nargs="+", help="Natural language query")
    search_p.add_argument("-n", "--top", type=int, default=5, help="Max results")
    search_p.add_argument("--tool", dest="search_tool", default=None,
                          help="Scope search to a specific tool's skills")

    learn_p = subparsers.add_parser("learn", help="Record a lesson (error->rule->skill loop)")
    learn_p.add_argument("lesson", help="One-line description of the lesson learned")
    learn_p.add_argument("--context", default="", help="Additional context or file paths")
    learn_p.add_argument("--tool", default="", help="Tool name this lesson applies to")
    learn_p.add_argument("--severity", default="info",
                         choices=["info", "warning", "critical"],
                         help="Severity: info (convention), warning (bug-prone), critical (data loss)")

    lessons_p = subparsers.add_parser("lessons", help="Show recent lessons")
    lessons_p.add_argument("--last", type=int, default=10, help="Number of recent lessons")
    lessons_p.add_argument("--tool", default="", help="Filter by tool name")

    analyze_p = subparsers.add_parser("analyze", help="Analyze lessons for patterns")
    analyze_p.add_argument("--days", type=int, default=30, help="Analyze lessons from last N days")
    analyze_p.add_argument("--tool", default="", help="Filter by tool name")

    suggest_p = subparsers.add_parser("suggest", help="Generate improvement suggestions")
    suggest_p.add_argument("--focus", default="all",
                           choices=["all", "security", "performance", "quality"],
                           help="Focus area for suggestions")

    apply_p = subparsers.add_parser("apply", help="Apply a suggestion (with action guide)")
    apply_p.add_argument("id", help="Suggestion ID (from 'SKILLS suggest')")

    history_p = subparsers.add_parser("history", help="Show evolution history")
    history_p.add_argument("--last", type=int, default=20, help="Number of entries")

    introspect_p = subparsers.add_parser("introspect", help="Analyze agent transcripts for behavior patterns")
    introspect_p.add_argument("--transcripts", type=int, default=5, help="Number of recent transcripts to analyze")

    market_p = subparsers.add_parser("market", help="Browse and install skills from marketplace")
    market_sub = market_p.add_subparsers(dest="market_source")

    market_sub.add_parser("sources", help="List available skill sources")
    market_sub.add_parser("installed", help="List installed marketplace skills")

    for src_id, src_help in [("clawhub", "ClawHub (OpenClaw) marketplace"),
                             ("openclaw-master", "Curated OpenClaw master skills")]:
        src_p = market_sub.add_parser(src_id, help=src_help)
        src_sub = src_p.add_subparsers(dest="market_action")

        browse_p = src_sub.add_parser("browse", help="Browse top skills")
        browse_p.add_argument("--limit", type=int, default=15, help="Max results")
        browse_p.add_argument("--category", default="top-downloads",
                              choices=["top-downloads", "top-stars", "newest", "certified"],
                              help="Browse category")

        search_p = src_sub.add_parser("search", help="Search for skills")
        search_p.add_argument("query", help="Search query")
        search_p.add_argument("--limit", type=int, default=15, help="Max results")

        install_p = src_sub.add_parser("install", help="Install a skill")
        install_p.add_argument("slug", help="Skill slug (e.g. cursor-agent)")

        uninstall_p = src_sub.add_parser("uninstall", help="Remove an installed marketplace skill")
        uninstall_p.add_argument("slug", help="Skill slug")

    if tool.handle_command_line(parser):
        return
    args, _ = parser.parse_known_args()

    BOLD = get_color("BOLD")
    RED = get_color("RED")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    if args.command == "list":
        skills = get_skills()
        if not skills:
            print("No skills found.")
            return
        for name, rel_path, desc, abs_path in skills:
            linked = (CURSOR_SKILLS_DIR / name).is_symlink()
            status = f"{GREEN}linked{RESET}" if linked else f"{RED}not linked{RESET}"
            category = str(rel_path.parent) if str(rel_path.parent) != "." else ""
            cat_label = f" ({category})" if category else ""
            print(f"  {BOLD}{name}{RESET}{cat_label}  [{status}]")
            if desc:
                print(f"    {desc}")
        return

    if args.command == "show":
        skill_file = _find_skill(args.name)
        if not skill_file:
            print(f"{BOLD}{RED}Error{RESET}: Skill '{args.name}' not found.")
            return
        print(skill_file.read_text())
        return

    if args.command == "search":
        from logic.search.tools import search_skills
        DIM = get_color("DIM", "\033[2m")
        query = " ".join(args.query)
        results = search_skills(
            Path(tool.project_root),
            query,
            top_k=args.top,
            tool_name=getattr(args, "search_tool", None),
        )
        if not results:
            print(f"  No results for: {query}")
            return
        for i, r in enumerate(results, 1):
            meta = r.get("meta", {})
            score_pct = int(r["score"] * 100)
            tool_tag = f" (tool: {meta['tool']})" if meta.get("tool") else ""
            print(f"  {BOLD}{i}. {r['id']}{RESET}{tool_tag} ({score_pct}%)")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")
        return

    if args.command == "sync":
        count = sync_skills()
        print(f"{BOLD}{GREEN}Synced{RESET} {count} skill(s) to {CURSOR_SKILLS_DIR}/")
        return

    if args.command == "path":
        print(str(LIBRARY_DIR))
        return

    if args.command == "learn":
        _record_lesson(args.lesson, args.context, args.tool, args.severity,
                       BOLD, GREEN, RESET)
        return

    if args.command == "lessons":
        _show_lessons(args.last, args.tool, BOLD, GREEN, RED, RESET)
        return

    if args.command == "analyze":
        YELLOW = get_color("YELLOW")
        _analyze_lessons(args.days, args.tool, BOLD, GREEN, RED, YELLOW, RESET)
        return

    if args.command == "suggest":
        YELLOW = get_color("YELLOW")
        _suggest_improvements(args.focus, BOLD, GREEN, RED, YELLOW, RESET)
        return

    if args.command == "apply":
        YELLOW = get_color("YELLOW")
        _apply_suggestion(args.id, BOLD, GREEN, RED, YELLOW, RESET)
        return

    if args.command == "history":
        from tool.SKILLS.logic.evolution import get_evolution_history
        entries = get_evolution_history(last_n=args.last)
        if not entries:
            print(f"  No evolution history yet. Use 'SKILLS apply <id>' to start.")
            return
        print(f"  {BOLD}Evolution History{RESET} (last {len(entries)}):")
        print()
        for e in entries:
            ts = e.get("timestamp", "?")[:16]
            status_color = GREEN if e.get("status") == "applied" else RED
            print(f"  {BOLD}{ts}{RESET} [{e.get('suggestion_id', '?')}] "
                  f"{status_color}{e.get('status', '?')}{RESET}")
            print(f"    {e.get('content', '')[:100]}")
        return

    if args.command == "introspect":
        from tool.SKILLS.logic.evolution import introspect
        print(f"  {BOLD}Analyzing{RESET} recent agent transcripts...")
        result = introspect(max_transcripts=args.transcripts)
        if not result:
            print(f"  No transcripts found.")
            return
        print(f"  {BOLD}Introspection Report{RESET}")
        print(f"  Transcripts analyzed: {result['transcripts_analyzed']}")
        print(f"  Total messages: {result['total_messages']} "
              f"(user: {result['user_messages']}, assistant: {result['assistant_messages']})")
        print(f"  Ratio (assistant/user): {result['ratio_assistant_to_user']}x")
        print()
        if result['tool_mentions']:
            print(f"  {BOLD}Tool Mentions{RESET} (top 15):")
            for tool, count in result['tool_mentions'].items():
                bar = "#" * min(count // 5, 30)
                print(f"    {tool:20s} {count:4d} {bar}")
            print()
        if result['error_keywords']:
            print(f"  {BOLD}Error Patterns{RESET}:")
            for keyword, count in result['error_keywords'].items():
                print(f"    {keyword:20s} {count:4d}")
            print()
        if result['improvement_opportunities']:
            print(f"  {BOLD}Improvement Opportunities{RESET}:")
            for opp in result['improvement_opportunities']:
                priority = opp['priority'].upper()
                color = RED if priority == "HIGH" else (get_color("YELLOW") if priority == "MEDIUM" else RESET)
                print(f"    [{color}{priority}{RESET}] {opp['message']}")
        return

    if args.command == "market":
        YELLOW = get_color("YELLOW")
        try:
            BLUE = get_color("BLUE")
        except Exception:
            BLUE = "\033[34m"
        if not getattr(args, "market_source", None):
            print(f"  Usage: SKILLS market <sources|installed|clawhub|openclaw-master> ...")
            return
        _handle_market(args, BOLD, GREEN, RED, YELLOW, BLUE, RESET)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
