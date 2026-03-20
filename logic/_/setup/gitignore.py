"""GitIgnore management for AITerminalTools.

Auto-generates .gitignore from base patterns + tool.json git_ignore entries.
Previously lived in logic/git/manager.py; moved here because it's exclusively
consumed by the setup flow (ToolEngine.install, TOOL --setup).
"""

import json
from pathlib import Path


class GitIgnoreManager:
    """
    Centralized manager for project-wide .gitignore.
    Allows tools to dynamically register ignore/track patterns via their tool.json.
    """
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.gitignore_path = self.project_root / ".gitignore"
        self.base_patterns = [
            "# --- Framework Core ---",
            "/*",
            "!/main.py",
            "!/setup.py",
            "!/tool.json",
            "!/README.md",
            "!/for_agent.md",
            "",
            "# --- Framework Directories ---",
            "!/logic/",
            "!/interface/",
            "!/test/",
            "!/tool/",
            "!/report/",
            "!/skills/",
            "!/research/",
            "!/runtime/",
            "!/hooks/",
            "!/workspace/",
            "!/migrate/",
            "",
            "# --- Transient Directories ---",
            "**/data/",
            "**/logs/",
            "**/tmp/",
            "",
            "# --- Resource Management ---",
            "# resource/ is only tracked on the tool branch (preserved by align_tool via git add -f)",
            "**/resource/",
            "",
            "# --- Python Patterns ---",
            "**/__pycache__/",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".Python",
            "env/",
            "venv/",
            ".venv/",
            "pip-log.txt",
            "pip-delete-this-directory.txt",
            "",
            "# --- System Patterns ---",
            ".DS_Store",
            "Thumbs.db",
            ""
        ]

    def get_tool_rules(self):
        """
        Scans all tools (including nested ones) for their 'tool.json' and extracts 'git_ignore' field.
        Also reads root tool.json. Converts relative patterns to project-relative patterns.
        """
        tool_dir = self.project_root / "tool"
        rules = {}

        all_json_paths = []
        root_json = self.project_root / "tool.json"
        if root_json.exists():
            all_json_paths.append(root_json)
        if tool_dir.exists():
            all_json_paths.extend(tool_dir.rglob("tool.json"))

        for tool_json_path in all_json_paths:
            tool_path = tool_json_path.parent
            try:
                rel_tool_path = tool_path.relative_to(self.project_root)
                tool_rel_root = "/" + "/".join(rel_tool_path.parts)
                tool_display_name = " / ".join(rel_tool_path.parts[1:])
            except ValueError:
                continue

            try:
                with open(tool_json_path, 'r') as f:
                    data = json.load(f)
                    rel_patterns = data.get("git_ignore")
                    if rel_patterns and isinstance(rel_patterns, list):
                        processed = []
                        for p in rel_patterns:
                            if p.startswith("root:"):
                                processed.append(p[5:])
                            elif p == "!":
                                processed.append(f"!{tool_rel_root}/")
                            elif p.startswith("!"):
                                inner = p[1:]
                                if not inner.startswith("/"): inner = "/" + inner
                                processed.append(f"!{tool_rel_root}{inner}")
                            else:
                                inner = p
                                if not inner.startswith("/"): inner = "/" + inner
                                processed.append(f"{tool_rel_root}{inner}")
                        rules[tool_display_name] = processed
            except Exception as e:
                print(f"Error reading {tool_json_path}: {e}")
        return rules

    def generate(self):
        """
        Generates the final .gitignore content by merging base patterns and tool-specific rules.
        """
        content = self.base_patterns.copy()
        tool_rules = self.get_tool_rules()

        if tool_rules:
            content.append("# --- Tool Specific Rules ---")
            for tool_name, patterns in sorted(tool_rules.items()):
                content.append(f"# {tool_name}")
                content.extend(patterns)
                content.append("")

        return "\n".join(content)

    def rewrite(self):
        """
        Writes the generated content to .gitignore.
        """
        content = self.generate()
        with open(self.gitignore_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True


def initialize_git_state(project_root):
    """
    Performs initial git setup: .gitignore generation and basic checks.
    """
    manager = GitIgnoreManager(project_root)
    manager.rewrite()
    return True
