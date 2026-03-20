"""Hook instance: skills_scan

Fires on before_tool_call. Searches for relevant skills/lessons based
on the semantic description provided by --call-register.

Outputs matched skills so the agent can decide whether to load them.
"""
from logic._.hooks.engine import HookInstance


class SkillsScanHook(HookInstance):
    name = "skills_scan"
    description = "Match relevant skills/lessons via semantic search before tool execution"
    event_name = "before_tool_call"
    enabled_by_default = True

    def execute(self, **kwargs):
        description = kwargs.get("description", "")
        tool = kwargs.get("tool")
        if not description:
            return {"matched_skills": []}

        matched = []
        try:
            project_root = tool.project_root if tool else None
            if project_root:
                matched = self._search_skills(str(project_root), description)
        except Exception:
            pass

        return {"matched_skills": matched}

    @staticmethod
    def _search_skills(project_root: str, query: str, max_results: int = 3):
        """Search skill descriptions for relevance to the query."""
        from pathlib import Path
        import json

        skills_dir = Path(project_root) / "skills"
        if not skills_dir.exists():
            return []

        candidates = []
        for skill_dir in skills_dir.rglob("SKILL.md"):
            content = skill_dir.read_text(errors="ignore")
            desc_line = ""
            for line in content.split("\n"):
                if line.startswith("description:"):
                    desc_line = line[len("description:"):].strip()
                    break
            if desc_line:
                candidates.append({
                    "name": skill_dir.parent.name,
                    "description": desc_line,
                    "path": str(skill_dir),
                })

        if not candidates:
            return []

        query_words = set(query.lower().split())
        scored = []
        for c in candidates:
            desc_words = set(c["description"].lower().split())
            overlap = len(query_words & desc_words)
            if overlap > 0:
                scored.append((overlap, c))

        scored.sort(key=lambda x: -x[0])
        return [s[1] for s in scored[:max_results]]
