"""TOOL --skills [list | show <name> | search <query>]

Skill discovery and display. Wraps the ToolBase._handle_skills_command
with EcoCommand interface for root-level invocation.
"""

from logic._._ import EcoCommand


class SkillsCommand(EcoCommand):
    name = "skills"
    usage = "TOOL --skills [list | show <name> | search <query>]"

    def handle(self, args):
        subcmd = args[0] if args else "list"

        if subcmd == "show" and len(args) > 1:
            return self._show(args[1])
        if subcmd == "search" and len(args) > 1:
            return self._search(" ".join(args[1:]))
        if subcmd == "list" or not args:
            return self._list()

        print(f"Usage: {self.usage}")
        return 1

    def _resolve_skill_path(self, name):
        """Locate a skill file by name across known locations."""
        skills_root = self.project_root / "skills"
        if skills_root.exists():
            for p in skills_root.rglob("SKILL.md"):
                if p.parent.name == name:
                    return p
        library = self.project_root / "tool" / "SKILLS" / "data" / "library" / name / "SKILL.md"
        if library.exists():
            return library
        for td in (self.project_root / "tool").iterdir():
            p = td / "skills" / name / "SKILL.md"
            if p.exists():
                return p
        return None

    def _show(self, name):
        path = self._resolve_skill_path(name)
        if path:
            print(path.read_text())
            return 0
        self.error(f"Skill '{name}' not found.")
        return 1

    def _search(self, query):
        try:
            from logic._.search.tools import search_skills
            results = search_skills(self.project_root, query, top_k=10)
        except ImportError:
            results = []

        if results:
            print(f"{self.BOLD}Found {len(results)} skill(s) matching '{query}':{self.RESET}\n")
            for i, r in enumerate(results, 1):
                meta = r.get("meta", {})
                score_pct = int(r["score"] * 100)
                tool_tag = f" (tool: {meta['tool']})" if meta.get("tool") else ""
                print(f"  {self.BOLD}{i}. {r['id']}{self.RESET}{tool_tag} ({score_pct}%)")
                print(f"     {self.DIM}{meta.get('path', '')}{self.RESET}")
        else:
            print(f"No skills found matching '{query}'.")
        return 0

    def _list(self):
        skills_dir = self.project_root / "tool" / "SKILLS" / "data" / "library"
        if not skills_dir.exists():
            self.info("No skills library found.")
            return 0

        names = sorted(
            d.name for d in skills_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )
        if names:
            self.header(f"{self.tool_name} Skills")
            for name in names:
                path = self._resolve_skill_path(name)
                desc = ""
                if path:
                    for line in path.read_text().splitlines():
                        if line.startswith("description:"):
                            desc = line[len("description:"):].strip()
                            break
                status = f"{self.GREEN}available{self.RESET}" if path else f"{self.YELLOW}not found{self.RESET}"
                print(f"  {self.BOLD}{name}{self.RESET}  [{status}]")
                if desc:
                    print(f"    {desc}")
            print(f"\n  Use '{self.tool_name} --skills show <name>' to view a skill.")
        else:
            self.info("No skills configured.")
        return 0
