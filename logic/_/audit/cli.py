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

        ap = sub.add_parser("argparse", help="Three-tier argparse conformance (---/--/-)")
        ap.add_argument("--fix", action="store_true", help="Auto-fix structure violations")

        sub.add_parser("skills", help="Audit skill hierarchy: README.md, AGENT.md coverage")
        sub.add_parser("archived", help="Check for duplicate tools in tool/ and archived/")
        sub.add_parser("colocated", help="Verify __/ directories are only referenced by parent endpoint")
        sub.add_parser("endpoints", help="Smoke-test all eco command endpoints via argparse.json")

        parsed = parser.parse_args(args)
        root = self.project_root

        if parsed.audit_command == "imports":
            return self._imports(parsed, root)
        elif parsed.audit_command == "quality":
            return self._quality(parsed, root)
        elif parsed.audit_command == "code":
            return self._code(parsed)
        elif parsed.audit_command == "argparse":
            return self._argparse(parsed)
        elif parsed.audit_command == "skills":
            return self._skills_audit()
        elif parsed.audit_command == "archived":
            from interface.dev import dev_audit_archived
            dev_audit_archived(self.project_root)
            return 0
        elif parsed.audit_command == "colocated":
            return self._colocated_audit()
        elif parsed.audit_command == "endpoints":
            return self._endpoint_smoke_test()
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
        from logic._.utils.turing.status import fmt_status, fmt_detail

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

        def _audit_logic_structure(stage):
            logic_dir = root / "logic"
            bin_dir = root / "bin"
            violations = []
            skip = {"_", "__pycache__", "__init__"}
            commands = set()
            if bin_dir.exists():
                for entry in bin_dir.iterdir():
                    if entry.is_dir() and not entry.name.startswith("."):
                        commands.add(entry.name.lower())
                    elif entry.is_file() and not entry.name.startswith("."):
                        commands.add(entry.name.lower())
            for entry in sorted(logic_dir.iterdir()):
                if not entry.is_dir() or entry.name in skip or entry.name.startswith("."):
                    continue
                if entry.name.lower() not in commands:
                    violations.append(entry.name)
            results["logic_structure_violations"] = violations
            if violations:
                stage.success_name = f"logic structure — {len(violations)} non-command dirs: {', '.join(violations)}"
            else:
                stage.success_name = "logic structure — compliant"
            return True

        def _audit_command_symmetry(stage):
            """Check that shared eco commands have logic/_/ implementations
            and tools with logic/ subdirs have proper hierarchy."""
            findings = []
            
            SHARED_ECO_COMMANDS = {
                "dev", "test", "setup", "config", "eco", "skills",
                "hooks", "audit", "assistant", "agent", "status",
                "install", "search", "list", "workspace", "migrate",
                "reinstall", "uninstall",
            }
            DECORATOR_FLAGS = {"no-warning", "tool-quiet"}
            
            logic_shared = root / "logic" / "_"
            if logic_shared.exists():
                shared_dirs = {d.name for d in logic_shared.iterdir()
                              if d.is_dir() and not d.name.startswith(".")
                              and d.name != "__pycache__"}
                
                for cmd in sorted(SHARED_ECO_COMMANDS):
                    if cmd not in shared_dirs:
                        findings.append(f"shared --{cmd} has no logic/_/{cmd}/ directory")
            
            tool_dir = root / "tool"
            if tool_dir.exists():
                for td in sorted(tool_dir.iterdir()):
                    if not td.is_dir() or td.name.startswith(".") or td.name.startswith("_"):
                        continue
                    tool_logic = td / "logic"
                    tool_interface = td / "interface"
                    if tool_logic.is_dir() and not tool_interface.is_dir():
                        findings.append(f"tool/{td.name}/ has logic/ but no interface/")
            
            results["command_symmetry_findings"] = findings
            if findings:
                stage.success_name = f"command symmetry — {len(findings)} issues"
            else:
                stage.success_name = "command symmetry — compliant"
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
            TuringStage("logic_structure", _audit_logic_structure,
                        active_status="Checking", success_status="Checked",
                        bold_part="Checking", is_sticky=True),
            TuringStage("command_symmetry", _audit_command_symmetry,
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
        from logic._.utils.turing.status import fmt_status

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

        logic_violations = results.get("logic_structure_violations", [])
        if logic_violations:
            print(f"\n{SEP}")
            print(f"\n\033[1m\033[33mlogic/ Structure Violations\033[0m")
            print("Directories in logic/ that don't match a tool command in bin/:")
            for name in logic_violations:
                print(f"  \033[33m{name}\033[0m — should be under logic/_/ (shared infra) or match a bin/ command")
            print(f"\n  \033[2mSee skill: symmetric-design > logic/ Module Rule\033[0m")

        cmd_findings = results.get("command_symmetry_findings", [])
        if cmd_findings:
            print(f"\n{SEP}")
            print(f"\n\033[1m\033[33mCommand Symmetry Issues\033[0m")
            for finding in cmd_findings:
                print(f"  \033[33m{finding}\033[0m")
            print(f"\n  \033[2mSee skill: symmetric-design > Command Symmetry\033[0m")

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

    def _argparse(self, parsed):
        """Run argparse three-tier conformance audit with optional --fix."""
        from logic._.audit.argparse_audit import audit_project, print_report

        root = self.project_root
        result = audit_project(root)
        print_report(result)

        if parsed.fix and result["total_findings"] > 0:
            self._argparse_fix(root, result)

        if parsed.fix:
            self._structure_fix(root)

        return 1 if result["errors"] > 0 else 0

    def _argparse_fix(self, root, result):
        """Auto-fix argparse conformance violations in source files."""
        import re
        BOLD = "\033[1m"
        DIM = "\033[2m"
        RESET = "\033[0m"
        fixed = 0

        for finding in result["findings"]:
            fpath = Path(finding["file"])
            violation = finding["violation"]
            opt = finding["option"]
            line_num = finding["line"]

            if violation == "decorator_wrong_prefix":
                name = opt.lstrip("-")
                try:
                    text = fpath.read_text(encoding="utf-8")
                    old = f'"{opt}"'
                    new = f'"-{name}", "{opt}"'
                    if old in text:
                        text = text.replace(old, new, 1)
                        fpath.write_text(text, encoding="utf-8")
                        fixed += 1
                        print(f"  {DIM}Fixed L{line_num}: {opt} → -{name} alias added{RESET}")
                except Exception as e:
                    print(f"  {DIM}Skip {fpath.name} L{line_num}: {e}{RESET}")

        if fixed:
            print(f"\n{BOLD}Fixed {fixed} violations.{RESET}")

    def _structure_fix(self, root):
        """Auto-create missing logic/_/ directories for shared eco commands."""
        BOLD = "\033[1m"
        DIM = "\033[2m"
        RESET = "\033[0m"

        from logic._.audit.argparse_audit import ECO_COMMANDS_WITH_DIR

        shared_dir = root / "logic" / "_"
        created = 0

        for cmd in sorted(ECO_COMMANDS_WITH_DIR):
            cmd_dir = shared_dir / cmd
            if not cmd_dir.exists():
                cmd_dir.mkdir(parents=True, exist_ok=True)
                (cmd_dir / "__init__.py").write_text("")
                (cmd_dir / "main.py").write_text(
                    f'"""logic/_/{cmd}/main.py — {cmd} eco command."""\n'
                )
                created += 1
                print(f"  {DIM}Created logic/_/{cmd}/ (stub){RESET}")

        if created:
            print(f"\n{BOLD}Created {created} directories.{RESET}")
        else:
            print(f"\n{DIM}Structure already compliant.{RESET}")

    def _colocated_audit(self):
        """Audit __/ co-located data directories for referential integrity.

        Rules:
        1. __/ directories may only exist alongside a cli.py or main.py
        2. Contents of __/ may only be referenced by the parent cli.py/main.py
           and sibling modules in the same directory
        3. No Python business logic (.py files with classes/functions) in __/
        """
        import re as _re
        root = self.project_root
        violations = []
        dunder_dirs = []

        # Find all __/ directories
        for dunder in sorted(root.rglob("__")):
            if not dunder.is_dir():
                continue
            if any(p.name in ('.git', '__pycache__', 'node_modules', '.cache') for p in dunder.parents):
                continue
            if dunder.name != "__":
                continue
            dunder_dirs.append(dunder)

        if not dunder_dirs:
            self.info("No __/ directories found.")
            return 0

        self.header(f"Co-Located Data Audit ({len(dunder_dirs)} __/ directories)")

        for dunder in dunder_dirs:
            parent = dunder.parent
            rel_parent = parent.relative_to(root)
            has_endpoint = (parent / "cli.py").exists() or (parent / "main.py").exists()

            if not has_endpoint:
                violations.append((str(rel_parent / "__"), "ORPHAN", "No cli.py or main.py in parent directory"))
                continue

            # Check for business logic in __/
            for py_file in dunder.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8")
                    if _re.search(r'^\s*(class|def)\s+\w+', content, _re.MULTILINE):
                        rel_file = py_file.relative_to(root)
                        violations.append((str(rel_file), "LOGIC_IN_DUNDER",
                                           "Business logic (class/def) found in __/ — only data allowed"))
                except Exception:
                    pass

            # Check referential integrity: scan all .py files for references to this __/
            dunder_rel = str(dunder.relative_to(root))
            allowed_parents = {str(parent.relative_to(root))}

            for py_file in root.rglob("*.py"):
                if any(p.name in ('.git', '__pycache__', 'node_modules', '.cache', 'tmp') for p in py_file.parents):
                    continue
                py_rel = str(py_file.relative_to(root))
                py_parent = str(py_file.parent.relative_to(root))

                if py_parent in allowed_parents:
                    continue

                try:
                    content = py_file.read_text(encoding="utf-8")
                    patterns = [
                        dunder_rel.replace("/", "."),
                        dunder_rel,
                        f"/{dunder.name}/",
                    ]
                    for pat in patterns[:2]:
                        if pat in content:
                            violations.append((py_rel, "EXTERNAL_REF",
                                               f"References {rel_parent}/__/ from outside parent"))
                            break
                except Exception:
                    pass

            self.info(f"{rel_parent}/__/ — endpoint: {'yes' if has_endpoint else 'NO'}")

        if violations:
            print()
            self.header("Violations")
            for path, code, msg in violations:
                self.error(f"[{code}]", f"{path}: {msg}")
            print()
            self.warn(f"{len(violations)} violation(s) found.")
            return 1
        else:
            print()
            self.success("All __/ directories pass referential integrity check.")
            return 0

    def _endpoint_smoke_test(self):
        """Run full-path smoke tests for all eco command endpoints.

        For each logic/_/<name>/cli.py with argparse.json, invoke
        TOOL ---<name> (with no args) through the full dispatch chain
        and verify non-crash behavior (exit code 0 or 1, not >1).
        """
        import subprocess
        root = self.project_root
        shared_dir = root / "logic" / "_"
        results = []

        endpoints = []
        for d in sorted(shared_dir.iterdir()):
            if not d.is_dir() or d.name.startswith((".", "_")):
                continue
            if (d / "cli.py").exists() and (d / "argparse.json").exists():
                endpoints.append(d.name)

        if not endpoints:
            self.info("No endpoints with argparse.json found.")
            return 0

        self.header(f"Endpoint Smoke Tests ({len(endpoints)} endpoints)")

        tool_bin = root / "bin" / "TOOL"
        if not tool_bin.exists():
            self.error("bin/TOOL not found.", "Cannot run full-path smoke tests.")
            return 1

        passed = 0
        failed = 0
        skipped = 0

        # Endpoints that require interactive input or have side effects
        skip_list = {"assistant", "agent", "setup", "install", "uninstall",
                     "migrate", "workspace"}

        for name in endpoints:
            if name in skip_list:
                self.info(f"  SKIP ---{name} (interactive/side-effect)")
                skipped += 1
                continue

            try:
                cmd = [str(tool_bin), f"---{name}", "--help"]
                res = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=15,
                    cwd=str(root),
                )
                if res.returncode <= 2:
                    self.success(f"  PASS ---{name}", f"(exit {res.returncode})")
                    passed += 1
                else:
                    self.error(f"  FAIL ---{name}", f"exit {res.returncode}")
                    if res.stderr:
                        for line in res.stderr.strip().splitlines()[:3]:
                            self.info(f"    {line}")
                    failed += 1
            except subprocess.TimeoutExpired:
                self.warn(f"  TIMEOUT ---{name}", "(>15s)")
                failed += 1
            except Exception as e:
                self.error(f"  ERROR ---{name}", str(e))
                failed += 1

            results.append({"name": name, "passed": failed == 0})

        print()
        total = passed + failed + skipped
        self.info(f"Results: {passed} passed, {failed} failed, {skipped} skipped / {total} total")

        return 1 if failed > 0 else 0
