"""TOOL --eco [subcommand]

Unified ecosystem navigation: dashboard, search, tool detail, skills, map, guide.
"""

import subprocess

from logic._._ import EcoCommand


class EcoNavCommand(EcoCommand):
    name = "eco"
    usage = "TOOL --eco [search|tool|skill|nav|tree|map|here|guide|recall|cmds|cmd]"

    def handle(self, args):
        subcmd = args[0] if args else ""
        rest = args[1:] if len(args) > 1 else []

        if subcmd in ("-h", "--help", "help"):
            self._help()
            return 0
        if not subcmd:
            self._dashboard()
            return 0

        dispatch = {
            "search": lambda: self._search(rest),
            "tool": lambda: self._tool(rest),
            "skill": lambda: self._skill(rest),
            "skills": lambda: self._skills_list(rest),
            "nav": lambda: self._skills_nav(rest),
            "tree": lambda: self._skills_tree(),
            "map": self._map,
            "here": lambda: self._here(rest),
            "guide": self._guide,
            "recall": lambda: self._recall(rest),
            "cmds": self._cmds,
            "cmd": lambda: self._cmd(rest),
        }

        handler = dispatch.get(subcmd)
        if handler:
            handler()
            return 0

        from interface.utils import suggest_commands
        known = list(dispatch.keys())
        matches = suggest_commands(subcmd, known, n=2, cutoff=0.4)
        if matches:
            print(f"  {self.BOLD}Unknown:{self.RESET} {subcmd}. Did you mean: {', '.join(matches)}?")
        else:
            print(f"  {self.BOLD}Unknown:{self.RESET} {subcmd}")
        self.info(f"{self.tool_name} --eco --help for available commands.")
        return 1

    def _help(self):
        print(f"\n{self.BOLD}{self.tool_name} --eco{self.RESET} — Ecosystem Navigation\n")
        print(f"  {self.BOLD}Explore{self.RESET}")
        print(f"    --eco                      Dashboard — tools, skills, brain overview")
        print(f"    --eco search <query>       Semantic search across all knowledge")
        print(f"    --eco tool <name>          Deep-dive into a specific tool")
        print(f"    --eco skill <name>         Read a development skill/pattern")
        print(f"    --eco nav [path]           Navigate skills dictionary tree (pwd-like)")
        print(f"    --eco tree                 Show full skills tree structure")
        print(f"    --eco map                  Ecosystem directory structure")
        print(f"    --eco here [cwd]           Context-aware help for current directory")
        print(f"\n  {self.BOLD}Remember{self.RESET}")
        print(f"    --eco recall <query>       Search brain memory (lessons, activity)")
        print(f"    --eco guide                Onboarding guide for new agents")
        print(f"\n  {self.BOLD}Shortcuts{self.RESET}")
        print(f"    --eco cmds                 List blueprint-defined shortcut commands")
        print(f"    --eco cmd <name>           Run a blueprint shortcut command")
        print(f"\n  {self.BOLD}Options{self.RESET}")
        print(f"    --eco search <q> --scope tools|skills|lessons|docs  Scoped search")
        print(f"    --eco search <q> -n 5      Limit results")
        print(f"    --eco search <q> --tool LLM  Scope to a tool")
        print(f"\n  {self.BOLD}Per-tool:{self.RESET} TOOL_NAME --eco (e.g., LLM --eco, GIT --eco)")
        print()

    def _dashboard(self):
        from interface.eco import eco_dashboard
        data = eco_dashboard(self.project_root)
        tools = data["tools"]
        skills = data["skills"]
        brain = data["brain"]
        ws = data.get("workspace")
        bp_cmds = data.get("blueprint_cmds", [])

        print(f"\n  {self.BOLD}Ecosystem Dashboard{self.RESET}")
        print(f"  {'─' * 44}")
        print(f"  {self.BOLD}Tools{self.RESET}:    {tools['installed']}/{tools['total']} installed")
        print(f"  {self.BOLD}Skills{self.RESET}:   {skills['core']} core, {skills['library']} library")
        print(f"  {self.BOLD}Brain{self.RESET}:    {brain['tasks_active']} active tasks, {brain['tasks_done']} done, {brain['lessons']} lessons")
        if brain.get("context_age_min", -1) >= 0:
            age = brain["context_age_min"]
            age_str = f"{age}m ago" if age < 60 else f"{age // 60}h{age % 60}m ago"
            print(f"  {self.BOLD}Context{self.RESET}:  updated {age_str}")
        else:
            print(f"  {self.BOLD}Context{self.RESET}:  {self.RED}not initialized{self.RESET}")
        if ws:
            print(f"  {self.BOLD}Workspace{self.RESET}: {ws['name']} ({self.DIM}{ws['path']}{self.RESET})")
        if bp_cmds:
            print(f"  {self.BOLD}Shortcuts{self.RESET}: {', '.join(bp_cmds)}")
        print(f"  {'─' * 44}")
        print(f"\n  {self.DIM}{self.tool_name} --eco --help for all commands.{self.RESET}")
        print(f"  {self.DIM}{self.tool_name} --eco guide for onboarding.{self.RESET}\n")

    def _search(self, rest):
        from interface.eco import eco_search

        if not rest:
            print(f"Usage: {self.tool_name} --eco search <query> [-n top] [--scope all|tools|skills|lessons|docs]")
            return
        query_parts, top_k, scope, tool_filter = [], 10, "all", None
        i = 0
        while i < len(rest):
            if rest[i] in ("-n", "--top") and i + 1 < len(rest):
                top_k = int(rest[i + 1]); i += 2
            elif rest[i] == "--scope" and i + 1 < len(rest):
                scope = rest[i + 1]; i += 2
            elif rest[i] == "--tool" and i + 1 < len(rest):
                tool_filter = rest[i + 1]; i += 2
            else:
                query_parts.append(rest[i]); i += 1
        query = " ".join(query_parts)
        results = eco_search(self.project_root, query, scope=scope, top_k=top_k, tool=tool_filter)
        if not results:
            print(f"  No results for: {query}")
            return
        self.format_search_results(results)

    def _tool(self, rest):
        from interface.eco import eco_tool

        name = rest[0] if rest else None
        if not name:
            print(f"Usage: {self.tool_name} --eco tool <TOOL_NAME>")
            return
        info = eco_tool(self.project_root, name)
        if not info:
            self.error("Not found:", name)
            return

        print(f"\n  {self.BOLD}{info['name']}{self.RESET}")
        if info.get("description"):
            print(f"  {info['description']}")
        print()
        checks = [
            ("README.md", info.get("has_readme")),
            ("AGENT.md", info.get("has_for_agent")),
            ("interface/main.py", info.get("has_interface")),
            ("hooks/", info.get("has_hooks")),
            ("test/", info.get("has_tests")),
        ]
        for label, ok in checks:
            marker = f"{self.GREEN}✓{self.RESET}" if ok else f"{self.DIM}·{self.RESET}"
            print(f"  {marker} {label}")
        if info.get("test_count"):
            print(f"    {self.DIM}{info['test_count']} test file(s){self.RESET}")
        if info.get("dependencies"):
            print(f"\n  {self.BOLD}Dependencies:{self.RESET} {', '.join(info['dependencies'])}")
        if info.get("interface_functions"):
            print(f"\n  {self.BOLD}Interface:{self.RESET}")
            for fn in info["interface_functions"][:10]:
                print(f"    {fn}()")
        print(f"\n  {self.BOLD}Actions:{self.RESET}")
        print(f"    {self.tool_name} --eco search \"{info['name']}\"  — search related knowledge")
        if info.get("has_for_agent"):
            print(f"    Read: tool/{info['name']}/AGENT.md")
        if info.get("has_readme"):
            print(f"    Read: tool/{info['name']}/README.md")
        print()

    def _skill(self, rest):
        from interface.eco import eco_skill
        name = rest[0] if rest else None
        if not name:
            self._skills_list(rest)
            return
        content = eco_skill(self.project_root, name)
        if not content:
            self.error("Not found:", name)
            return
        print(content)

    def _skills_list(self, rest):
        """List all available skills."""
        skills_root = self.project_root / "skills"
        library = self.project_root / "tool" / "SKILLS" / "data" / "library"

        all_skills = {}
        for search_dir in [skills_root, library]:
            if not search_dir or not search_dir.exists():
                continue
            for sf in search_dir.rglob("SKILL.md"):
                name = sf.parent.name
                if name not in all_skills:
                    all_skills[name] = sf

        if all_skills:
            self.header(f"{self.tool_name} Skills")
            for name in sorted(all_skills):
                loc = all_skills[name]
                desc = ""
                for line in loc.read_text().splitlines():
                    if line.startswith("description:"):
                        desc = line[len("description:"):].strip()
                        break
                print(f"  {self.BOLD}{name}{self.RESET}")
                if desc:
                    print(f"    {desc}")
            print(f"\n  Use '{self.tool_name} --eco skill <name>' to view a skill.")
        else:
            self.info("No skills configured.")

    def _skills_nav(self, rest):
        """Delegate to SkillsCommand.nav for dictionary-tree navigation."""
        from logic._.skills.command import SkillsCommand
        sc = SkillsCommand(project_root=self.project_root, tool_name=self.tool_name)
        sc._nav(" ".join(rest) if rest else "")

    def _skills_tree(self):
        """Delegate to SkillsCommand.tree for full tree display."""
        from logic._.skills.command import SkillsCommand
        sc = SkillsCommand(project_root=self.project_root, tool_name=self.tool_name)
        sc._tree()

    def _map(self):
        from interface.eco import eco_map
        emap = eco_map(self.project_root)
        print(f"\n  {self.BOLD}Ecosystem Map{self.RESET}  {self.DIM}{emap['root']}{self.RESET}\n")
        for dirname, info in emap["directories"].items():
            if not info["exists"]:
                continue
            children_str = ""
            if info["children"]:
                children_str = (f"  {self.DIM}[{', '.join(info['children'][:8])}"
                                + (f", +{len(info['children']) - 8}" if len(info["children"]) > 8 else "")
                                + f"]{self.RESET}")
            print(f"  {self.BOLD}{dirname}{self.RESET}  {info['purpose']}")
            if children_str:
                print(f"  {children_str}")
        print()

    def _here(self, rest):
        from interface.eco import eco_here
        cwd = rest[0] if rest else None
        ctx = eco_here(self.project_root, cwd)
        print(f"\n  {self.BOLD}CWD:{self.RESET} {ctx['cwd']}")
        if not ctx.get("in_project"):
            self.info("Outside project.")
            if ctx.get("suggestion"):
                print(f"  {ctx['suggestion']}")
            return
        print(f"  {self.BOLD}Level:{self.RESET} {ctx['level']}")
        if ctx.get("tool"):
            print(f"  {self.BOLD}Tool:{self.RESET} {ctx['tool']}")
        if ctx.get("module"):
            print(f"  {self.BOLD}Module:{self.RESET} {ctx['module']}")
        if ctx.get("docs"):
            print(f"\n  {self.BOLD}Docs here:{self.RESET}")
            for d in ctx["docs"]:
                print(f"    {self.DIM}{d}{self.RESET}")
        if ctx.get("actions"):
            print(f"\n  {self.BOLD}Suggested:{self.RESET}")
            for a in ctx["actions"]:
                print(f"    {a}")
        print()

    def _guide(self):
        from interface.eco import eco_guide
        print(eco_guide(self.project_root))

    def _recall(self, rest):
        query = " ".join(rest) if rest else ""
        if not query:
            print(f"Usage: {self.tool_name} --eco recall <query>")
            return
        subprocess.run(["python3", str(self.project_root / "bin" / "BRAIN"), "recall", query])

    def _cmds(self):
        from interface.eco import eco_blueprint_commands
        cmds = eco_blueprint_commands(self.project_root)
        if not cmds:
            print(f"  No blueprint commands defined.")
            self.info("Add 'commands' to your brain blueprint JSON.")
            return
        print(f"\n  {self.BOLD}Blueprint Commands{self.RESET}\n")
        for name, defn in cmds.items():
            if isinstance(defn, str):
                print(f"  {self.BOLD}{name}{self.RESET}")
                print(f"    {self.DIM}$ {defn}{self.RESET}")
            else:
                desc = defn.get("description", "")
                run_cmd = defn.get("run", "")
                print(f"  {self.BOLD}{name}{self.RESET}  {desc}")
                print(f"    {self.DIM}$ {run_cmd}{self.RESET}")
        self.info(f"Run: {self.tool_name} --eco cmd <name>")

    def _cmd(self, rest):
        from interface.eco import eco_run_command
        cmd_name = rest[0] if rest else None
        if not cmd_name:
            print(f"Usage: {self.tool_name} --eco cmd <command_name>")
            return
        cmd_str = eco_run_command(self.project_root, cmd_name)
        if not cmd_str:
            self.error("Not found:", cmd_name)
            self.info(f"Run {self.tool_name} --eco cmds to see available commands.")
            return
        print(f"  {self.BOLD}Running:{self.RESET} {self.DIM}{cmd_str}{self.RESET}")
        subprocess.run(cmd_str, shell=True, cwd=str(self.project_root))
