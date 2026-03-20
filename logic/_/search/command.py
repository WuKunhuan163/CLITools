"""TOOL --search {tools,interfaces,skills,lessons,discoveries,docs,all} <query>

Semantic search across the project knowledge base.
"""

from logic._._ import EcoCommand


class SearchCommand(EcoCommand):
    name = "search"
    usage = "TOOL --search {tools|skills|lessons|docs|all} <query>"

    def handle(self, args):
        parser = self.create_parser("Semantic search across project")
        sub = parser.add_subparsers(dest="search_target")

        for name, help_text, defaults in [
            ("tools", "Search tools by natural language", 5),
            ("tools-deep", "Search tools at section/command level", 10),
            ("interfaces", "Search tool interfaces", 5),
            ("skills", "Search skills", 5),
            ("lessons", "Search lessons by semantic similarity", 5),
            ("discoveries", "Search discoveries", 5),
            ("docs", "Search project documentation", 10),
            ("all", "Search across all knowledge", 10),
        ]:
            sp = sub.add_parser(name, help=help_text)
            sp.add_argument("query", nargs="+", help="Search query")
            sp.add_argument("-n", "--top", type=int, default=defaults, help="Max results")
            if name in ("skills", "lessons", "discoveries", "all"):
                sp.add_argument("--tool", dest=f"{name}_tool", default=None,
                                help="Scope to a specific tool")

        parsed = parser.parse_args(args)
        if not parsed.search_target:
            parser.print_help()
            return 0

        from interface.search import (
            search_tools, search_interfaces, search_skills,
            search_tools_deep, search_lessons, search_discoveries,
            search_docs, search_all,
        )

        query = " ".join(parsed.query)
        top_k = parsed.top

        target_fn_map = {
            "tools": lambda: search_tools(self.project_root, query, top_k=top_k),
            "tools-deep": lambda: search_tools_deep(self.project_root, query, top_k=top_k),
            "interfaces": lambda: search_interfaces(self.project_root, query, top_k=top_k),
            "skills": lambda: search_skills(
                self.project_root, query, top_k=top_k,
                tool_name=getattr(parsed, "skills_tool", None)),
            "lessons": lambda: search_lessons(
                self.project_root, query, top_k=top_k,
                tool=getattr(parsed, "lessons_tool", None)),
            "discoveries": lambda: search_discoveries(
                self.project_root, query, top_k=top_k,
                tool=getattr(parsed, "discoveries_tool", None)),
            "docs": lambda: search_docs(self.project_root, query, top_k=top_k),
            "all": lambda: search_all(
                self.project_root, query, top_k=top_k,
                tool=getattr(parsed, "all_tool", None)),
        }

        fn = target_fn_map.get(parsed.search_target)
        if not fn:
            parser.print_help()
            return 0

        results = fn()
        if not results:
            print(f"  No results for: {query}")
            return 0

        self.format_search_results(results)
        return 0
