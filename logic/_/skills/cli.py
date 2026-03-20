"""TOOL --skills [list | show <name> | search <query> | nav [path] | tree]

Skill discovery, display, and navigation. Supports dictionary-tree
browsing with pwd-like awareness.
"""

from pathlib import Path

from logic._._ import EcoCommand


class SkillsCommand(EcoCommand):
    name = "skills"
    usage = "TOOL --skills [list | show <name> | search <query> | nav [path] | tree]"

    def handle(self, args):
        subcmd = args[0] if args else "list"

        if subcmd == "show" and len(args) > 1:
            return self._show(args[1])
        if subcmd == "search" and len(args) > 1:
            return self._search(" ".join(args[1:]))
        if subcmd == "nav":
            return self._nav(args[1] if len(args) > 1 else "")
        if subcmd == "tree":
            return self._tree()
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

    def _nav(self, path_str):
        """Navigate the skills dictionary tree like a filesystem.

        Usage:
          nav              → show root (skills/)
          nav development  → show skills/development/
          nav _/modularization → show skills/_/modularization/
          nav ..           → go up one level
        """
        skills_root = self.project_root / "skills"
        if not skills_root.exists():
            self.error("skills/ directory not found.")
            return 1

        if path_str == "..":
            path_str = ""

        target = skills_root / path_str if path_str else skills_root
        if not target.exists() or not target.is_dir():
            self.error(f"Path not found: skills/{path_str}")
            return 1

        rel = target.relative_to(self.project_root)

        # Show current location (pwd)
        print(f"\n  {self.BOLD}📂 {rel}/{self.RESET}")

        # Show AGENT.md guidance if available
        fa = target / "AGENT.md"
        if fa.exists():
            lines = fa.read_text().splitlines()
            guidance = []
            for line in lines:
                if line.startswith("#"):
                    continue
                if line.strip():
                    guidance.append(line.strip())
                if len(guidance) >= 3:
                    break
            if guidance:
                print(f"  {self.DIM}{' '.join(guidance[:2])}{self.RESET}\n")

        # List contents
        subdirs = sorted(d for d in target.iterdir()
                         if d.is_dir() and not d.name.startswith(".") and d.name != "__pycache__")
        files = sorted(f for f in target.iterdir()
                       if f.is_file() and f.suffix == ".md" and f.name == "SKILL.md")

        if files:
            skill_md = files[0]
            desc = ""
            for line in skill_md.read_text().splitlines():
                if line.startswith("description:"):
                    desc = line[len("description:"):].strip().strip('"')
                    break
            print(f"  {self.GREEN}SKILL.md{self.RESET}")
            if desc:
                print(f"    {self.DIM}{desc[:80]}{self.RESET}")

        for d in subdirs:
            has_skill = (d / "SKILL.md").exists()
            has_children = any(c.is_dir() and not c.name.startswith(".") for c in d.iterdir())

            if has_skill:
                desc = ""
                for line in (d / "SKILL.md").read_text().splitlines():
                    if line.startswith("description:"):
                        desc = line[len("description:"):].strip().strip('"')
                        break
                print(f"  {self.BOLD}{d.name}/{self.RESET}")
                if desc:
                    print(f"    {self.DIM}{desc[:70]}{self.RESET}")
            elif has_children:
                child_count = sum(1 for _ in d.rglob("SKILL.md"))
                print(f"  {self.BOLD}{d.name}/{self.RESET}  {self.DIM}({child_count} skills){self.RESET}")

        print(f"\n  {self.DIM}Navigate: TOOL --skills nav <subdir>{self.RESET}")
        if path_str:
            parent = str(Path(path_str).parent) if "/" in path_str else ""
            print(f"  {self.DIM}Go up:    TOOL --skills nav {parent or '..'}{self.RESET}")
        return 0

    def _tree(self):
        """Show the full skills tree structure."""
        skills_root = self.project_root / "skills"
        if not skills_root.exists():
            self.error("skills/ directory not found.")
            return 1

        print(f"\n{self.BOLD}Skills Dictionary Tree{self.RESET}\n")

        def _print_tree(path, prefix="", is_last=True):
            name = path.name
            connector = "└── " if is_last else "├── "

            has_skill = (path / "SKILL.md").exists()
            has_children = any(d.is_dir() and not d.name.startswith(".")
                               and d.name != "__pycache__" for d in path.iterdir())

            if has_skill:
                desc = ""
                for line in (path / "SKILL.md").read_text().splitlines():
                    if line.startswith("description:"):
                        desc = line[len("description:"):].strip().strip('"')
                        break
                label = f"{name}/"
                short_desc = f" {self.DIM}— {desc[:50]}{'...' if len(desc) > 50 else ''}{self.RESET}" if desc else ""
                print(f"{prefix}{connector}{label}{short_desc}")
            elif has_children:
                print(f"{prefix}{connector}{self.BOLD}{name}/{self.RESET}")

            if has_children:
                children = sorted(d for d in path.iterdir()
                                  if d.is_dir() and not d.name.startswith(".")
                                  and d.name != "__pycache__")
                for i, child in enumerate(children):
                    child_is_last = (i == len(children) - 1)
                    extension = "    " if is_last else "│   "
                    _print_tree(child, prefix + extension, child_is_last)

        top_dirs = sorted(d for d in skills_root.iterdir()
                          if d.is_dir() and not d.name.startswith("."))
        for i, d in enumerate(top_dirs):
            _print_tree(d, "", i == len(top_dirs) - 1)

        total = sum(1 for _ in skills_root.rglob("SKILL.md"))
        print(f"\n  {self.DIM}{total} skills total{self.RESET}\n")
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
