"""TOOL --audit {imports,quality,code,--lang}

Code quality audits: import rules, hooks/interfaces validation, dead code detection,
and language/localization audits.
"""

from pathlib import Path

from logic._._ import EcoCommand


class AuditCommand(EcoCommand):
    name = "audit"
    usage = "TOOL --audit {imports|quality|code} [--lang <code>] [options]"

    def handle(self, args):
        if "--lang" in args:
            return self._handle_lang(args)

        parser = self.create_parser("Code quality audits")
        sub = parser.add_subparsers(dest="audit_command")

        ip = sub.add_parser("imports", help="Audit cross-tool import quality")
        ip.add_argument("--tool", help="Audit specific tool only")
        ip.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
        ip.add_argument("--exclude", help="Comma-separated tool names to skip")
        ip.add_argument("--docs", action="store_true", help="Also audit documentation files")

        qp = sub.add_parser("quality", help="Audit hooks, interfaces, and skills")
        qp.add_argument("--tool", help="Audit specific tool only")
        qp.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
        qp.add_argument("--exclude", help="Comma-separated tool names to skip")
        qp.add_argument("--no-skills", action="store_true", help="Skip skills audit")

        cp = sub.add_parser("code", help="Dead code, unused imports/variables, syntax errors")
        cp.add_argument("--fix", action="store_true", help="Auto-fix safe issues")
        cp.add_argument("--targets", nargs="*", help="Directories to scan")

        parsed = parser.parse_args(args)
        root = self.project_root

        if parsed.audit_command == "imports":
            return self._imports(parsed, root)
        elif parsed.audit_command == "quality":
            return self._quality(parsed, root)
        elif parsed.audit_command == "code":
            return self._code(parsed)
        else:
            parser.print_help()
        return 0

    def _handle_lang(self, args):
        """Handle --audit --lang <code> [list|--force|--turing|--detect]."""
        lang_idx = args.index("--lang")
        rest = args[lang_idx + 1:]

        if not rest or rest[0] == "list":
            from interface.lang import list_languages
            list_languages(self.project_root, translation_func=self._)
            return 0

        if rest[0] == "--detect" or "--detect" in rest:
            return self._detect_hardcoded(rest)

        lang_code = rest[0]
        force = "--force" in rest
        turing = "--turing" in rest

        from interface.lang import audit_lang
        audit_lang(lang_code, self.project_root,
                   force=force, turing=turing,
                   translation_func=self._)
        return 0

    def _detect_hardcoded(self, rest):
        """Detect hardcoded user-facing strings not wrapped in _()."""
        from logic._.lang.detect import detect_all, format_report

        targets = [r for r in rest if not r.startswith("-") and r != "--detect"]
        report = detect_all(self.project_root, targets=targets or None)
        print(format_report(report))
        return 0

    def _imports(self, parsed, root):
        from interface.audit import (
            audit_imports_all, audit_imports_tool, audit_imports_docs,
            format_imports_report, imports_to_json,
        )
        exclude = [x.strip() for x in (parsed.exclude or "").split(",") if x.strip()]
        if parsed.tool:
            tool_dir = root / "tool" / parsed.tool
            if not tool_dir.exists():
                self.error(f"Tool not found: {parsed.tool}")
                return 1
            issues = audit_imports_tool(tool_dir, root)
            results = {parsed.tool: issues} if issues else {}
            print(imports_to_json(results) if parsed.as_json else format_imports_report(results))
        else:
            results = audit_imports_all(root, exclude=exclude or ["GOOGLE.CDMCP"])
            if getattr(parsed, "docs", False):
                doc_issues = audit_imports_docs(root)
                if doc_issues:
                    results["__docs__"] = doc_issues
            print(imports_to_json(results) if parsed.as_json else format_imports_report(results))
        return 0

    def _quality(self, parsed, root):
        from interface.audit import (
            audit_all_quality, audit_tool_quality, audit_skills,
            format_quality_report, quality_to_json,
        )
        exclude = [x.strip() for x in (parsed.exclude or "").split(",") if x.strip()]
        skills_issues = None if parsed.no_skills else audit_skills(root)
        if parsed.tool:
            tool_dir = root / "tool" / parsed.tool
            if not tool_dir.exists():
                self.error(f"Tool not found: {parsed.tool}")
                return 1
            tool_res = audit_tool_quality(tool_dir, root)
            results = {parsed.tool: tool_res} if tool_res else {}
            print(quality_to_json(results, skills_issues) if parsed.as_json
                  else format_quality_report(results, skills_issues))
        else:
            results = audit_all_quality(root, exclude=exclude)
            print(quality_to_json(results, skills_issues) if parsed.as_json
                  else format_quality_report(results, skills_issues))
        return 0

    def _code(self, parsed):
        from interface.audit import run_full_audit, print_report
        report = run_full_audit(targets=parsed.targets or None, auto_fix=parsed.fix)
        print_report(report)
        return 0
