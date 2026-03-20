"""TOOL --audit {imports,quality,code,--lang}

Code quality audits: import rules, hooks/interfaces validation, dead code detection,
and language/localization audits. Run with no args for a full-flow audit.
"""

from pathlib import Path

from logic._._ import EcoCommand


class AuditCommand(EcoCommand):
    name = "audit"
    usage = "TOOL --audit [imports|quality|code] [--lang <code>] [options]"

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

        sub.add_parser("skills", help="Audit skill hierarchy: README.md, AGENT.md coverage")
        sub.add_parser("archived", help="Check for duplicate tools in tool/ and archived/")

        parsed = parser.parse_args(args)
        root = self.project_root

        if parsed.audit_command == "imports":
            return self._imports(parsed, root)
        elif parsed.audit_command == "quality":
            return self._quality(parsed, root)
        elif parsed.audit_command == "code":
            return self._code(parsed)
        elif parsed.audit_command == "skills":
            return self._skills_audit()
        elif parsed.audit_command == "archived":
            from interface.dev import dev_audit_archived
            dev_audit_archived(self.project_root)
            return 0
        elif not args or parsed.audit_command is None:
            return self._full_flow()
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

    def _full_flow(self):
        """Run all audit phases with Turing machine progress display."""
        from interface.turing import ProgressTuringMachine, TuringStage
        from interface.audit import (
            audit_imports_all, audit_all_quality, audit_skills,
            run_full_audit,
        )
        from logic._.lang.detect import detect_all
        from logic.utils.turing.status import fmt_status, fmt_detail

        root = self.project_root
        results = {}

        def _audit_imports(stage):
            r = audit_imports_all(root, exclude=["GOOGLE.CDMCP"])
            total = sum(len(v) for v in r.values())
            errors = sum(1 for v in r.values() for i in v if i.severity == "error")
            warnings = total - errors
            results["imports"] = r
            results["imports_summary"] = (len(r), errors, warnings)
            if errors:
                stage.success_name = f"imports — {errors} errors, {warnings} warnings ({len(r)} tools)"
            else:
                stage.success_name = "imports — no issues"
            return True

        def _audit_quality(stage):
            r = audit_all_quality(root, exclude=[])
            skills = audit_skills(root)
            all_issues = []
            for cats in r.values():
                for issues in cats.values():
                    all_issues.extend(issues)
            errors = sum(1 for i in all_issues if i.severity == "error")
            warnings = sum(1 for i in all_issues if i.severity == "warning")
            infos = len(all_issues) - errors - warnings
            results["quality"] = r
            results["skills"] = skills
            results["quality_summary"] = (len([t for t, c in r.items()
                                                if any(c.values())]), errors, warnings, infos)
            parts = []
            if errors:
                parts.append(f"{errors} errors")
            if warnings:
                parts.append(f"{warnings} warnings")
            if infos:
                parts.append(f"{infos} info")
            stage.success_name = f"quality — {', '.join(parts)}" if parts else "quality — no issues"
            return True

        def _audit_code(stage):
            report = run_full_audit()
            results["code"] = report
            total = report.total
            if total:
                stage.success_name = f"code — {total} issues"
            else:
                stage.success_name = "code — no issues"
            return True

        def _audit_localization(stage):
            report = detect_all(root)
            results["lang"] = report
            n = report["total_findings"]
            f = report["files_with_findings"]
            if n:
                stage.success_name = f"localization — {n} hardcoded strings ({f} files)"
            else:
                stage.success_name = "localization — no hardcoded strings"
            return True

        def _audit_skills_hierarchy(stage):
            skills_root = root / "skills"
            issues = 0
            if skills_root.exists():
                for dirpath in skills_root.rglob("*"):
                    if not dirpath.is_dir() or dirpath.name.startswith("."):
                        continue
                    has_skill = (dirpath / "SKILL.md").exists()
                    has_subdirs = any(d.is_dir() and not d.name.startswith(".") for d in dirpath.iterdir())
                    if has_subdirs and not has_skill:
                        if not (dirpath / "README.md").exists():
                            issues += 1
                        if not (dirpath / "AGENT.md").exists():
                            issues += 1
            if issues:
                stage.success_name = f"skills hierarchy — {issues} missing docs"
            else:
                stage.success_name = "skills hierarchy — complete"
            results["skills_hierarchy_issues"] = issues
            return True

        def _audit_archived(stage):
            tool_dir = root / "tool"
            archived_dir = root / "logic" / "_" / "install" / "archived"
            if not archived_dir.exists():
                archived_dir = root / "logic" / "_" / "install" / "archived"
            active = set()
            archived = set()
            if tool_dir.exists():
                active = {d.name for d in tool_dir.iterdir() if d.is_dir() and not d.name.startswith(".")}
            if archived_dir.exists():
                archived = {d.name for d in archived_dir.iterdir() if d.is_dir() and not d.name.startswith(".")}
            dupes = active & archived
            results["archived_duplicates"] = sorted(dupes)
            if dupes:
                stage.success_name = f"archived — {len(dupes)} duplicates: {', '.join(sorted(dupes))}"
            else:
                stage.success_name = "archived — no duplicates"
            return True

        stages = [
            TuringStage("imports", _audit_imports,
                        active_status="Auditing", success_status="Audited",
                        bold_part="Auditing", is_sticky=True),
            TuringStage("quality", _audit_quality,
                        active_status="Auditing", success_status="Audited",
                        bold_part="Auditing", is_sticky=True),
            TuringStage("code", _audit_code,
                        active_status="Auditing", success_status="Audited",
                        bold_part="Auditing", is_sticky=True),
            TuringStage("localization", _audit_localization,
                        active_status="Scanning", success_status="Scanned",
                        bold_part="Scanning", is_sticky=True),
            TuringStage("skills_hierarchy", _audit_skills_hierarchy,
                        active_status="Checking", success_status="Checked",
                        bold_part="Checking", is_sticky=True),
            TuringStage("archived", _audit_archived,
                        active_status="Checking", success_status="Checked",
                        bold_part="Checking", is_sticky=True),
        ]

        pm = ProgressTuringMachine(stages, project_root=str(root))
        pm.run(final_newline=True)

        self._print_full_report(results)
        return 0

    def _print_full_report(self, results):
        """Print unified detail report from all audit phases."""
        from interface.audit import format_imports_report, format_quality_report
        from logic._.audit.code_quality import print_report as print_code_report
        from logic._.lang.detect import format_report as format_detect_report
        from logic.utils.turing.status import fmt_status

        SEP = "\033[2m" + "─" * 60 + "\033[0m"

        imp = results.get("imports", {})
        if imp:
            print(f"\n{SEP}")
            print(format_imports_report(imp))

        qual = results.get("quality", {})
        skills = results.get("skills")
        if qual and any(any(c.values()) for c in qual.values()):
            print(f"\n{SEP}")
            print(format_quality_report(qual, skills))

        code_r = results.get("code")
        if code_r and code_r.total:
            print(f"\n{SEP}")
            print_code_report(code_r)

        lang = results.get("lang", {})
        if lang.get("total_findings", 0):
            print(f"\n{SEP}")
            top_files = sorted(lang["findings"].items(),
                               key=lambda x: len(x[1]), reverse=True)[:5]
            print(f"\n\033[1mLocalization — Top files with hardcoded strings\033[0m")
            for fpath, findings in top_files:
                print(f"  {fpath} ({len(findings)})")
                for f in findings[:3]:
                    s = f["string"][:60]
                    print(f"    \033[2mL{f['line']:4d} \"{s}\"\033[0m")
                if len(findings) > 3:
                    print(f"    \033[2m... and {len(findings) - 3} more\033[0m")
            print(f"\n  \033[2mRun TOOL --audit --lang --detect for full report.\033[0m")

        dupes = results.get("archived_duplicates", [])
        if dupes:
            print(f"\n{SEP}")
            print(f"\n\033[1m\033[31mArchived Tool Conflicts\033[0m")
            print("Tools found in both tool/ and archived/:")
            for name in dupes:
                print(f"  \033[31m{name}\033[0m")
            print(f"\n  \033[2mRemove from archived/ before deploying.\033[0m")

    def _skills_audit(self):
        """Audit the skills hierarchy for documentation coverage."""
        root = self.project_root
        skills_root = root / "skills"
        if not skills_root.exists():
            self.error("skills/ directory not found.")
            return 1

        issues = []
        total_dirs = 0
        total_skills = 0

        for dirpath in sorted(skills_root.rglob("*")):
            if not dirpath.is_dir():
                continue
            if dirpath.name.startswith(".") or dirpath.name == "__pycache__":
                continue

            has_skill = (dirpath / "SKILL.md").exists()
            has_subdirs = any(
                d.is_dir() and not d.name.startswith(".")
                for d in dirpath.iterdir()
            )
            is_category = has_subdirs and not has_skill

            if has_skill:
                total_skills += 1

            if is_category:
                total_dirs += 1
                rel = dirpath.relative_to(root)
                if not (dirpath / "README.md").exists():
                    issues.append(("error", str(rel), "Missing README.md (category directory)"))
                if not (dirpath / "AGENT.md").exists():
                    issues.append(("warning", str(rel), "Missing AGENT.md (category directory)"))

        for td in sorted((root / "tool").iterdir()):
            sd = td / "skills"
            if sd.exists() and sd.is_dir() and any(sd.iterdir()):
                tool_name = td.name
                rel = sd.relative_to(root)
                if not (sd / "README.md").exists():
                    issues.append(("warning", str(rel), f"Tool {tool_name} skills/ missing README.md"))
                if not (sd / "AGENT.md").exists():
                    issues.append(("info", str(rel), f"Tool {tool_name} skills/ missing AGENT.md"))

        BOLD = "\033[1m"
        RED = "\033[31m"
        YELLOW = "\033[33m"
        CYAN = "\033[36m"
        GREEN = "\033[32m"
        RESET = "\033[0m"

        print(f"\n{BOLD}Skills Hierarchy Audit{RESET}")
        print("=" * 60)
        print(f"Category directories: {total_dirs}")
        print(f"Skill documents: {total_skills}")
        print(f"Issues: {len(issues)}\n")

        if not issues:
            print(f"{GREEN}{BOLD}All skill directories have proper documentation.{RESET}")
        else:
            errors = [i for i in issues if i[0] == "error"]
            warnings = [i for i in issues if i[0] == "warning"]
            infos = [i for i in issues if i[0] == "info"]

            for sev, path, msg in errors:
                print(f"  {RED}ERROR  {RESET} {path}")
                print(f"         {msg}")
            for sev, path, msg in warnings:
                print(f"  {YELLOW}WARNING{RESET} {path}")
                print(f"         {msg}")
            for sev, path, msg in infos:
                print(f"  {CYAN}INFO   {RESET} {path}")
                print(f"         {msg}")

        print()
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
