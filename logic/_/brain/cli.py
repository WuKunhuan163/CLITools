"""TOOL ---brain — Agent brain management eco command.

Manages tasks, activity logging, context snapshots, session instances,
and self-reflection. Each tool's brain data lives in data/_/runtime/.

Usage:
    TOOL ---brain list                     List all tasks
    TOOL ---brain add "description"        Add a new task
    TOOL ---brain done <id>                Mark task as done
    TOOL ---brain status                   Show dashboard
    TOOL ---brain snapshot "summary"       Save context.md
    TOOL ---brain recall "query"           Search institutional memory
    TOOL ---brain log "entry"              Record activity
    TOOL ---brain reflect                  Self-check protocol
    TOOL ---brain session list|create|switch|export|load|migrate
"""

import sys
import json
import time
from pathlib import Path
from collections import Counter

from logic._._ import EcoCommand
from logic._.agent.brain_tasks import (
    add_task, update_task, complete_task, delete_task,
    clear_done, clear_all, list_tasks, migrate_from_md,
)


class BrainCommand(EcoCommand):
    name = "brain"
    usage = "TOOL ---brain <command> [options]"

    def handle(self, args):
        root = str(self.project_root)
        if not args or args[0] in ("-h", "--help", "help"):
            return self._show_help()

        cmd = args[0]
        rest = args[1:]

        dispatch = {
            "list": lambda: self._cmd_list(root),
            "add": lambda: self._cmd_add(root, rest),
            "done": lambda: self._cmd_done(root, rest),
            "progress": lambda: self._cmd_update(root, rest, "in_progress"),
            "verify": lambda: self._cmd_update(root, rest, "verify_pending"),
            "delete": lambda: self._cmd_delete(root, rest),
            "clear-done": lambda: self._cmd_clear(root, "done"),
            "clear-all": lambda: self._cmd_clear(root, "all"),
            "note": lambda: self._cmd_note(root, rest),
            "migrate": lambda: self._cmd_migrate(root),
            "status": lambda: self._cmd_status(root),
            "snapshot": lambda: self._cmd_snapshot(root, rest),
            "recall": lambda: self._cmd_recall(root, rest),
            "log": lambda: self._cmd_log(root, rest),
            "digest": lambda: self._cmd_digest(root),
            "reflect": lambda: self._cmd_reflect(root, rest),
            "session": lambda: self._cmd_session(root, rest),
        }

        handler = dispatch.get(cmd)
        if handler:
            handler()
            return 0

        known = list(dispatch.keys())
        import difflib
        matches = difflib.get_close_matches(cmd, known, n=2, cutoff=0.5)
        self.error(f"Unknown command: {cmd}")
        if matches:
            self.info(f"Did you mean: {', '.join(matches)}?")
        return self._show_help()

    def _show_help(self):
        self.header(f"{self.tool_name} ---brain")
        print(__doc__)
        return 0

    # ── Task CRUD ──

    def _cmd_list(self, root):
        tasks = list_tasks(root)
        if not tasks:
            self.success("Brain:", detail="no tasks.")
            return
        active = [t for t in tasks if t["status"] != "done"]
        done = [t for t in tasks if t["status"] == "done"]
        status_map = {
            "in_progress": f"{self.BOLD}IN_PROGRESS{self.RESET}",
            "pending": "pending",
            "done": f"{self.GREEN}done{self.RESET}",
            "verify_pending": f"{self.BOLD}VERIFY_PENDING{self.RESET}",
        }
        if active:
            for t in active:
                sd = status_map.get(t["status"], t["status"])
                print(f"  #{t['id']:>3}  [{sd}]  {t['content']}")
                if t.get("notes"):
                    print(f"        {self.DIM}{t['notes']}{self.RESET}")
        if done:
            if active:
                print()
            for t in done[-5:]:
                print(f"  {self.DIM}#{t['id']:>3}  [done]  {t['content']}{self.RESET}")
        print(f"\n{self.DIM}{len(active)} active, {len(done)} done{self.RESET}")

    def _cmd_add(self, root, rest):
        if not rest:
            self.error("Missing task description.")
            return
        content = " ".join(rest)
        t = add_task(root, content)
        self.success("Added.", detail=f"#{t['id']}: {content}")

    def _cmd_done(self, root, rest):
        if not rest:
            self.error("Missing task ID.")
            return
        tid = int(rest[0])
        t = complete_task(root, tid)
        if t:
            self.success("Done.", detail=f"#{tid}: {t['content']}")
        else:
            self.error("Not found.", detail=f"#{tid}")

    def _cmd_update(self, root, rest, status):
        if not rest:
            self.error("Missing task ID.")
            return
        tid = int(rest[0])
        t = update_task(root, tid, status=status)
        if t:
            label = status.replace("_", " ").title()
            self.success(f"{label}.", detail=f"#{tid}: {t['content']}")
        else:
            self.error("Not found.", detail=f"#{tid}")

    def _cmd_delete(self, root, rest):
        if not rest:
            self.error("Missing task ID.")
            return
        tid = int(rest[0])
        if delete_task(root, tid):
            self.success("Deleted.", detail=f"#{tid}")
        else:
            self.error("Not found.", detail=f"#{tid}")

    def _cmd_clear(self, root, scope):
        n = clear_done(root) if scope == "done" else clear_all(root)
        self.success("Cleared.", detail=f"{n} {'done ' if scope == 'done' else ''}tasks.")

    def _cmd_note(self, root, rest):
        if len(rest) < 2:
            self.error("Usage: ---brain note <id> \"note text\"")
            return
        tid = int(rest[0])
        note = " ".join(rest[1:])
        t = update_task(root, tid, notes=note)
        if t:
            self.success("Updated.", detail=f"#{tid} notes.")
        else:
            self.error("Not found.", detail=f"#{tid}")

    def _cmd_migrate(self, root):
        n = migrate_from_md(root)
        if n:
            self.success("Migrated.", detail=f"{n} tasks from tasks.md to tasks.json.")
        else:
            self.info("Nothing to migrate (tasks.json already exists or tasks.md empty).")

    # ── Dashboard ──

    def _cmd_status(self, root):
        tasks = list_tasks(root)
        active = [t for t in tasks if t["status"] != "done"]
        done = [t for t in tasks if t["status"] == "done"]
        in_progress = [t for t in tasks if t["status"] == "in_progress"]

        self.header("Agent Brain Dashboard")
        print(f"  {'─' * 40}")
        print(f"  {self.BOLD}Tasks{self.RESET}: {len(active)} active, {len(done)} done")
        for t in in_progress:
            print(f"    {self.GREEN}>{self.RESET} #{t['id']}: {t['content']}")

        lessons_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl"
        lesson_count = 0
        recent_lesson = ""
        if lessons_file.exists():
            lines = [l for l in lessons_file.read_text().strip().split("\n") if l.strip()]
            lesson_count = len(lines)
            if lines:
                try:
                    last = json.loads(lines[-1])
                    recent_lesson = last.get("lesson", "")[:80]
                except Exception:
                    pass
        print(f"  {self.BOLD}Lessons{self.RESET}: {lesson_count} total")
        if recent_lesson:
            print(f"    {self.DIM}Latest: {recent_lesson}{self.RESET}")

        context_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "context.md"
        if context_file.exists():
            age_sec = time.time() - context_file.stat().st_mtime
            if age_sec < 60:
                age_str = f"{int(age_sec)}s ago"
            elif age_sec < 3600:
                age_str = f"{int(age_sec/60)}m ago"
            else:
                age_str = f"{int(age_sec/3600)}h{int((age_sec%3600)/60)}m ago"
            print(f"  {self.BOLD}Context{self.RESET}: updated {age_str}")
        else:
            print(f"  {self.BOLD}Context{self.RESET}: {self.RED}not initialized{self.RESET}")

        skills_dir = Path(root) / "skills"
        skill_count = 0
        if skills_dir.exists():
            for d in skills_dir.rglob("SKILL.md"):
                skill_count += 1
        print(f"  {self.BOLD}Skills{self.RESET}: {skill_count} skills")
        print(f"  {'─' * 40}\n")

    # ── Context management ──

    def _cmd_snapshot(self, root, rest):
        if not rest:
            self.error("Missing summary text.")
            return
        summary = " ".join(rest)
        context_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "context.md"
        context_file.parent.mkdir(parents=True, exist_ok=True)

        tasks = list_tasks(root)
        active = [t for t in tasks if t["status"] != "done"]
        in_progress = [t for t in active if t["status"] == "in_progress"]
        done_recent = [t for t in tasks if t["status"] == "done"][-5:]

        lines = [
            "# Current Context", "",
            f"**Last updated:** {time.strftime('%Y-%m-%d %H:%M')}",
            f"**Working on:** {in_progress[0]['content'] if in_progress else 'No active task'}",
            f"**Summary:** {summary}", "",
        ]
        if active:
            lines.append("## Active Tasks")
            for t in active:
                s = "IN_PROGRESS" if t["status"] == "in_progress" else t["status"]
                lines.append(f"- [{s}] #{t['id']}: {t['content']}")
            lines.append("")
        if done_recent:
            lines.append("## Recently Completed")
            for t in done_recent:
                lines.append(f"- #{t['id']}: {t['content']}")
            lines.append("")

        activity_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "activity.jsonl"
        if activity_file.exists():
            recent = []
            for line in activity_file.read_text().strip().split("\n"):
                if line.strip():
                    try:
                        recent.append(json.loads(line))
                    except Exception:
                        continue
            recent = recent[-10:]
            if recent:
                lines.append("## Recent Activity")
                for act in recent:
                    ts = act.get("timestamp", "")[:16]
                    entry = act.get("entry", "")[:100]
                    files = act.get("files", [])
                    fstr = f" → {', '.join(files)}" if files else ""
                    lines.append(f"- [{ts}] {entry}{fstr}")
                lines.append("")

        context_file.write_text("\n".join(lines), encoding="utf-8")
        self.success("Snapshot saved.", detail=str(context_file))

    def _cmd_recall(self, root, rest):
        if not rest:
            self.error("Missing query.")
            return
        query = " ".join(rest)
        query_lower = query.lower()
        found = []

        lessons_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl"
        if lessons_file.exists():
            for line in lessons_file.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    text = obj.get("lesson", "") + " " + obj.get("context", "")
                    if query_lower in text.lower():
                        sev = obj.get("severity", "info")
                        tool = obj.get("tool", "")
                        ts = obj.get("timestamp", "")[:10]
                        prefix = f"[{sev}]" + (f" [{tool}]" if tool else "")
                        found.append(f"  {self.DIM}{ts}{self.RESET} {prefix} {obj.get('lesson', '')[:120]}")
                except Exception:
                    continue

        activity_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "activity.jsonl"
        if activity_file.exists():
            for line in activity_file.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    entry = obj.get("entry", "")
                    if query_lower in entry.lower():
                        ts = obj.get("timestamp", "")[:16]
                        files = obj.get("files", [])
                        fhint = f" [{', '.join(files)}]" if files else ""
                        found.append(f"  {self.DIM}{ts}{self.RESET} [activity]{fhint} {entry[:120]}")
                except Exception:
                    continue

        if found:
            self.header(f"Recall: {len(found)} matches for '{query}'")
            for item in found[:20]:
                print(item)
        else:
            self.info(f"No matches for '{query}'")

    # ── Activity logging ──

    def _cmd_log(self, root, rest):
        files_list = None
        task_ref = None
        entry_parts = []
        i = 0
        while i < len(rest):
            if rest[i] == "--files" and i + 1 < len(rest):
                files_list = [f.strip() for f in rest[i + 1].split(",")]
                i += 2
            elif rest[i] == "--task" and i + 1 < len(rest):
                task_ref = rest[i + 1]
                i += 2
            else:
                entry_parts.append(rest[i])
                i += 1

        entry = " ".join(entry_parts)
        if not entry:
            self.error("Missing log entry text.")
            return

        log_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "activity.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "entry": entry}
        if files_list:
            record["files"] = files_list
        if task_ref:
            record["task"] = task_ref
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        detail_parts = []
        if files_list:
            detail_parts.append(f"files: {', '.join(files_list)}")
        if task_ref:
            detail_parts.append(f"task: {task_ref}")
        detail = f" ({'; '.join(detail_parts)})" if detail_parts else ""
        self.success("Logged.", detail=f"{entry[:80]}{detail}")

    # ── Digest ──

    def _cmd_digest(self, root):
        lessons_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl"
        if not lessons_file.exists():
            self.info("No lessons found.")
            return

        tool_counts = Counter()
        keywords = Counter()
        total = 0
        for line in lessons_file.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                total += 1
                tool = obj.get("tool", "general")
                if tool:
                    tool_counts[tool] += 1
                text = (obj.get("lesson", "") + " " + obj.get("context", "")).lower()
                for word in text.split():
                    if len(word) > 4 and word.isalpha():
                        keywords[word] += 1
            except Exception:
                continue

        self.header(f"Digest: {total} lessons total")
        if tool_counts:
            print(f"\n  {self.BOLD}By tool:{self.RESET}")
            for tool, count in tool_counts.most_common(10):
                marker = " ← consolidate?" if count >= 3 else ""
                print(f"    {tool}: {count}{marker}")

        frequent = [(w, c) for w, c in keywords.most_common(20) if c >= 3]
        consolidation_tools = [t for t, c in tool_counts.most_common(10) if c >= 3]
        if frequent or consolidation_tools:
            print(f"\n  {self.BOLD}Action required:{self.RESET}")
            for t in consolidation_tools:
                print(f"    SKILLS create {t}-patterns  ({tool_counts[t]} lessons)")
        else:
            self.info("No recurring themes yet. Keep recording lessons.")

    # ── Reflect ──

    def _cmd_reflect(self, root, rest):
        tool_name = None
        i = 0
        while i < len(rest):
            if rest[i] == "--tool" and i + 1 < len(rest):
                tool_name = rest[i + 1]
                i += 2
            else:
                i += 1

        reflection_file = Path(root) / "for_agent_reflection.md"
        if not reflection_file.exists():
            self.error("Not found.", detail="for_agent_reflection.md")
            return

        content = reflection_file.read_text(encoding="utf-8")

        if "## Self-Check Protocol" in content:
            start = content.index("## Self-Check Protocol")
            rest_content = content[start:]
            end = rest_content.find("\n## ", 1)
            if end < 0:
                end = len(rest_content)
            protocol = rest_content[:end].strip()
            self.header("Self-Check Protocol")
            for line in protocol.split("\n")[2:]:
                if line.startswith("**"):
                    name = line.split("**")[1] if "**" in line else line
                    print(f"  {self.BOLD}{name}{self.RESET}")
                elif line.startswith("- "):
                    print(f"    {self.DIM}{line[2:]}{self.RESET}")
            print()

        self.header("Active Reminders")
        for r in [
            "Minimal emphasis: bold status labels only, no emojis",
            "Search TOOL ---eco search before creating anything new",
            "Use absolute paths in tool call arguments",
            "After structural changes: update README.md + AGENT.md",
            "After each task: TOOL ---brain log, reflect, then USERINPUT --hint",
        ]:
            print(f"  {self.DIM}{r}{self.RESET}")
        print()

        lessons_file = Path(root) / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl"
        if lessons_file.exists():
            tool_counts = Counter()
            for line in lessons_file.read_text(encoding="utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    t = obj.get("tool", "general")
                    if t:
                        tool_counts[t] += 1
                except Exception:
                    continue
            clusters = [(t, c) for t, c in tool_counts.most_common(5) if c >= 3]
            if clusters:
                self.header("Creation Opportunities")
                for t, count in clusters:
                    print(f"  {self.DIM}{count} lessons on {t} — run:{self.RESET} "
                          f"{self.BOLD}SKILLS create {t}-patterns{self.RESET}")
                print()

        if "## Current System Gaps" in content:
            start = content.index("## Current System Gaps")
            rest_content = content[start:]
            end = rest_content.find("\n## ", 1)
            if end < 0:
                end = len(rest_content)
            gaps_section = rest_content[:end].strip()
            gap_lines = []
            for line in gaps_section.split("\n"):
                if line.startswith("**Gap:"):
                    cleaned = line.lstrip("*").strip()
                    if cleaned.startswith("Gap:"):
                        cleaned = cleaned[4:].strip()
                    dash = cleaned.find("—")
                    if dash > 0:
                        name = cleaned[:dash].strip().rstrip("*")
                        desc = cleaned[dash + 1:].strip().rstrip("*")
                        gap_lines.append((name, desc))
            if gap_lines:
                self.header(f"Current System Gaps ({len(gap_lines)})")
                for name, desc in gap_lines:
                    print(f"  {self.BOLD}{name}{self.RESET}")
                    print(f"    {self.DIM}{desc[:100]}{self.RESET}")
                print()

        if tool_name:
            tool_reflection = Path(root) / "tool" / tool_name / "for_agent_reflection.md"
            self.header(f"Tool Reflection: {tool_name}")
            if tool_reflection.exists():
                tool_content = tool_reflection.read_text(encoding="utf-8")
                for section in ("## Known Gaps", "## Observations"):
                    if section in tool_content:
                        start = tool_content.index(section)
                        rest_content = tool_content[start:]
                        end = rest_content.find("\n## ", 1)
                        if end < 0:
                            end = len(rest_content)
                        for line in rest_content[:end].strip().split("\n")[2:]:
                            if line.strip():
                                print(f"  {self.DIM}{line.strip()}{self.RESET}")
                        break
                else:
                    self.info("No gaps or observations recorded yet.")
            else:
                self.info(f"No for_agent_reflection.md. Create: tool/{tool_name}/for_agent_reflection.md")
            print()

        self.info("Next: USERINPUT --hint (report results to user)")

    # ── Session management ──

    def _cmd_session(self, root, rest):
        if not rest:
            self.error("Usage: ---brain session [list|types|create|switch|export|load|migrate|manifest]")
            return

        from logic._.brain.instance import BrainSessionManager
        mgr = BrainSessionManager(root)
        subcmd = rest[0]
        sub_rest = rest[1:]

        if subcmd == "list":
            sessions = mgr.list_sessions()
            if not sessions:
                self.info("No sessions. Run: TOOL ---brain session migrate")
                return
            self.header(f"Brain Sessions ({len(sessions)})")
            for s in sessions:
                marker = f" {self.GREEN}(active){self.RESET}" if s.get("active") else ""
                tasks = f", {s.get('tasks', 0)} tasks" if "tasks" in s else ""
                activity = f", {s.get('activity_entries', 0)} activity" if "activity_entries" in s else ""
                print(f"  {self.BOLD}{s['name']}{self.RESET}{marker}{tasks}{activity}")
                if s.get("updated"):
                    print(f"    {self.DIM}updated: {s['updated']}{self.RESET}")

        elif subcmd == "types":
            types = mgr.list_types()
            if not types:
                self.info("No brain types found.")
                return
            self.header(f"Brain Types ({len(types)})")
            for t in types:
                desc = t.get("description", "")[:80]
                ver = t.get("version", "")
                ver_str = f" v{ver}" if ver else ""
                print(f"  {self.BOLD}{t['name']}{self.RESET}{ver_str}")
                if desc:
                    print(f"    {self.DIM}{desc}{self.RESET}")

        elif subcmd == "create" and sub_rest:
            name = sub_rest[0]
            brain_type = None
            i = 1
            while i < len(sub_rest):
                if sub_rest[i] == "--type" and i + 1 < len(sub_rest):
                    brain_type = sub_rest[i + 1]
                    i += 2
                else:
                    i += 1
            try:
                path = mgr.create_session(name, brain_type=brain_type)
                type_msg = f" (type: {brain_type})" if brain_type else ""
                self.success("Created.", detail=f"{type_msg} {path}")
            except FileExistsError as e:
                self.error("Already exists.", detail=str(e))
            except FileNotFoundError as e:
                self.error("Type not found.", detail=str(e))

        elif subcmd == "switch" and sub_rest:
            try:
                mgr.switch_session(sub_rest[0])
                self.success("Switched.", detail=f"Active brain: {sub_rest[0]}")
            except FileNotFoundError as e:
                self.error("Not found.", detail=str(e))

        elif subcmd == "export" and sub_rest:
            try:
                zip_path = mgr.export_session(sub_rest[0])
                self.success("Exported.", detail=str(zip_path))
            except FileNotFoundError as e:
                self.error("Not found.", detail=str(e))

        elif subcmd == "load" and sub_rest:
            zip_path = Path(sub_rest[0])
            name = sub_rest[1] if len(sub_rest) > 1 else None
            try:
                loaded = mgr.load_session(zip_path, name)
                self.success("Loaded.", detail=f"Session: {loaded}")
            except (FileExistsError, FileNotFoundError) as e:
                self.error("Failed.", detail=str(e))

        elif subcmd == "migrate":
            result = mgr.migrate_flat_to_session()
            if result:
                self.success("Migrated.", detail="Flat files → sessions/default/")
            else:
                self.info("Already migrated. sessions/default/ exists")

        elif subcmd == "manifest":
            name = sub_rest[0] if sub_rest else mgr.active_session()
            mgr._generate_manifest(name)
            manifest_path = mgr.session_path(name) / "MANIFEST.md"
            self.success("Generated.", detail=str(manifest_path))

        else:
            self.error("Unknown session command.", detail=subcmd)
            self.info("Usage: ---brain session [list|types|create|switch|export|load|migrate|manifest]")
