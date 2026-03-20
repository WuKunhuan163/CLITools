"""EcoCommand — base class for shared eco command endpoints (cli.py).

Each logic/_/<name>/cli.py that handles a --- eco command inherits from this class.
The base tool discovers these automatically via directory traversal — no registration needed.

Architecture:
  main.py (tool root) → base argparse (stateless routing) → cli.py (concrete endpoint)

The base provides:
  - Color palette access
  - Project root discovery
  - Translation helper
  - Formatted output (error, success, info, warn)
  - Common argument parsing utilities
"""

from pathlib import Path
from typing import Optional, Callable, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _default_translation(key, default, **kwargs):
    return default.format(**kwargs) if kwargs else default


class EcoCommand:
    """Base class for all symmetric ecosystem commands."""

    name: str = ""
    usage: str = ""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        tool_name: str = "TOOL",
        translation_func: Optional[Callable] = None,
    ):
        self.project_root = project_root or _PROJECT_ROOT
        self.tool_name = tool_name
        self._ = translation_func or _default_translation
        self._colors_loaded = False
        self._color_cache = {}

    def _ensure_colors(self):
        if self._colors_loaded:
            return
        from logic._.config import get_color
        for name, fallback in [
            ("BOLD", "\033[1m"), ("DIM", "\033[2m"),
            ("RED", "\033[31m"), ("GREEN", "\033[32m"),
            ("YELLOW", "\033[33m"), ("BLUE", "\033[34m"),
            ("WHITE", "\033[37m"), ("RESET", "\033[0m"),
        ]:
            self._color_cache[name] = get_color(name, fallback)
        self._colors_loaded = True

    def __getattr__(self, name):
        palette = {"BOLD", "DIM", "RED", "GREEN", "YELLOW", "BLUE", "WHITE", "RESET"}
        if name in palette:
            self._ensure_colors()
            return self._color_cache[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def handle(self, args: List[str]) -> int:
        """Execute the command. Override in subclass. Returns exit code."""
        raise NotImplementedError(f"{type(self).__name__}.handle() not implemented")

    def print_usage(self):
        if self.usage:
            print(f"  Usage: {self.usage}")

    def error(self, msg: str, detail: str = ""):
        self._ensure_colors()
        out = f"  {self.BOLD}{self.RED}{msg}{self.RESET}"
        if detail:
            out += f" {self.DIM}{detail}{self.RESET}"
        print(out)

    def success(self, msg: str, detail: str = ""):
        self._ensure_colors()
        out = f"  {self.BOLD}{self.GREEN}{msg}{self.RESET}"
        if detail:
            out += f" {detail}"
        print(out)

    def warn(self, msg: str, detail: str = ""):
        self._ensure_colors()
        out = f"  {self.BOLD}{self.YELLOW}{msg}{self.RESET}"
        if detail:
            out += f" {self.DIM}{detail}{self.RESET}"
        print(out)

    def info(self, msg: str):
        self._ensure_colors()
        print(f"  {self.DIM}{msg}{self.RESET}")

    def header(self, title: str):
        self._ensure_colors()
        print(f"\n{self.BOLD}{title}{self.RESET}")

    def table_row(self, *cols, widths=None):
        """Print a formatted table row with optional column widths."""
        if not widths:
            print("  " + "  ".join(str(c) for c in cols))
            return
        parts = []
        for col, w in zip(cols, widths):
            parts.append(f"{col:<{w}}")
        print("  " + "".join(parts))

    def create_parser(self, description: str = "", **kwargs):
        """Create an argparse.ArgumentParser pre-configured with tool/command name."""
        import argparse
        return argparse.ArgumentParser(
            prog=f"{self.tool_name} ---{self.name}",
            description=description or f"{self.tool_name} ---{self.name}",
            **kwargs,
        )

    def format_search_results(self, results: list):
        """Print formatted search results — shared across --search and --eco."""
        self._ensure_colors()
        for i, r in enumerate(results, 1):
            meta = r.get("meta", {})
            score_pct = int(r["score"] * 100)
            rtype = meta.get("type", "unknown")

            if rtype == "tool":
                desc = meta.get("description") or meta.get("purpose") or ""
                flags = []
                if meta.get("has_readme"):
                    flags.append("README")
                if meta.get("has_for_agent"):
                    flags.append("for_agent")
                tag = f" [{', '.join(flags)}]" if flags else ""
                print(f"  {self.BOLD}{i}. {r['id']}{self.RESET} ({score_pct}%){tag}")
                if desc:
                    print(f"     {desc}")
                print(f"     {self.DIM}{meta.get('path', '')}{self.RESET}")
            elif rtype in ("section", "command"):
                tool_name = meta.get("tool", "?")
                heading = meta.get("heading", "") or meta.get("command", "")
                preview = meta.get("preview", "")[:100]
                src = meta.get("source", "")
                file_path = meta.get("path", "")
                label = f"{tool_name} > {heading}" if heading else tool_name
                extra = f" [{src}]" if src else ""
                print(f"  {self.BOLD}{i}. {label}{self.RESET} ({score_pct}%){extra}")
                if preview:
                    print(f"     {self.DIM}{preview}{self.RESET}")
                if file_path and rtype == "section":
                    print(f"     {self.DIM}-> {file_path}{self.RESET}")
            elif rtype == "interface":
                print(f"  {self.BOLD}{i}. {r['id']}{self.RESET} interface ({score_pct}%)")
                print(f"     {self.DIM}{meta.get('path', '')}{self.RESET}")
            elif rtype == "skill":
                tool_tag = f" [{meta['tool']}]" if meta.get("tool") else ""
                print(f"  {self.BOLD}{i}. {r['id']}{self.RESET}{tool_tag} ({score_pct}%)")
                print(f"     {self.DIM}{meta.get('path', '')}{self.RESET}")
            elif rtype == "lesson":
                sev = meta.get("severity", "info")
                tool_tag = f" [{meta['tool']}]" if meta.get("tool") else ""
                lesson_text = meta.get("lesson", "")[:120]
                ts = meta.get("timestamp", "")[:10]
                print(f"  {self.BOLD}{i}. Lesson{self.RESET}{tool_tag} ({score_pct}%) [{sev}] {ts}")
                print(f"     {lesson_text}")
            elif rtype == "discovery":
                tool_tag = f" [{meta['tool']}]" if meta.get("tool") else ""
                content = meta.get("content", "")[:120]
                ts = meta.get("timestamp", "")[:10]
                print(f"  {self.BOLD}{i}. Discovery{self.RESET}{tool_tag} ({score_pct}%) {ts}")
                print(f"     {content}")
            elif rtype in ("doc", "doc_section"):
                source = meta.get("source", "")
                heading = meta.get("heading", "")
                level = meta.get("level", "")
                module = meta.get("module", "")
                preview = meta.get("preview", "")[:100]
                label = module or source or r["id"]
                if heading:
                    label = f"{label} > {heading}"
                level_tag = f" [{level}]" if level else ""
                print(f"  {self.BOLD}{i}. {label}{self.RESET} ({score_pct}%){level_tag}")
                if preview:
                    print(f"     {self.DIM}{preview}{self.RESET}")
                print(f"     {self.DIM}{meta.get('path', '')}{self.RESET}")
