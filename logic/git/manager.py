import os
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
            "!/.gitignore",
            "!/.gitattributes",
            "",
            "# --- Framework Directories ---",
            "!/logic/",
            "!/bin/",
            "!/test/",
            "!/tool/",
            "",
            "# --- Transient Directories ---",
            "/data/",
            "/logs/",
            "/tmp/",
            "/resource/",
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
        Scans all tools for their 'tool.json' and extracts 'git_ignore' field.
        Converts relative patterns to project-relative patterns.
        """
        tool_dir = self.project_root / "tool"
        rules = {}
        if not tool_dir.exists():
            return rules

        for tool_path in tool_dir.iterdir():
            if not tool_path.is_dir():
                continue
            
            tool_name = tool_path.name
            tool_json_path = tool_path / "tool.json"
            
            if tool_json_path.exists():
                try:
                    with open(tool_json_path, 'r') as f:
                        data = json.load(f)
                        rel_patterns = data.get("git_ignore")
                        if rel_patterns and isinstance(rel_patterns, list):
                            # Convert relative tool patterns to project-relative patterns
                            # e.g. "!" -> "!/tool/TOOL_NAME/"
                            # e.g. "data/" -> "/tool/TOOL_NAME/data/"
                            tool_rel_root = f"/tool/{tool_name}"
                            
                            processed = []
                            for p in rel_patterns:
                                if p == "!":
                                    processed.append(f"!{tool_rel_root}/")
                                elif p.startswith("!"):
                                    # Handle negation like "!src/" -> "!/tool/TOOL_NAME/src/"
                                    inner = p[1:]
                                    if not inner.startswith("/"): inner = "/" + inner
                                    processed.append(f"!{tool_rel_root}{inner}")
                                else:
                                    # Handle ignore like "data/" -> "/tool/TOOL_NAME/data/"
                                    inner = p
                                    if not inner.startswith("/"): inner = "/" + inner
                                    processed.append(f"{tool_rel_root}{inner}")
                            rules[tool_name] = processed
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
