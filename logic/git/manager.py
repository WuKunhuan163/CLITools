import os
import json
from pathlib import Path

class GitIgnoreManager:
    """
    Centralized manager for project-wide .gitignore.
    Allows tools to dynamically register ignore/track patterns.
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
        Scans all tools for a 'git_ignore.json' file or 'logic/git_ignore.json'.
        Returns a dictionary of tool_name -> list of patterns.
        """
        tool_dir = self.project_root / "tool"
        rules = {}
        if not tool_dir.exists():
            return rules

        for tool_path in tool_dir.iterdir():
            if not tool_path.is_dir():
                continue
            
            tool_name = tool_path.name
            # Look for git_ignore.json in tool root or tool/logic/
            paths = [
                tool_path / "git_ignore.json",
                tool_path / "logic" / "git_ignore.json"
            ]
            
            for p in paths:
                if p.exists():
                    try:
                        with open(p, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                rules[tool_name] = data
                            elif isinstance(data, dict) and "patterns" in data:
                                rules[tool_name] = data["patterns"]
                    except Exception as e:
                        print(f"Error reading {p}: {e}")
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
    # Placeholder for other initialization logic (e.g. LFS check)
    return True

