"""Write quality checks for agent-created files.

Extracted from the LLM conversation manager to be reusable across
all agent modes. Detects common quality issues in HTML, CSS, and
Python files.
"""
import os
import re
from typing import List


def check_write_quality(path: str, content: str) -> List[str]:
    """Run automated quality checks on a written file.

    Returns a list of warning strings. Empty list means all checks passed.
    """
    warnings = []
    ext = os.path.splitext(path)[1].lower()

    if ext == ".py":
        try:
            compile(content, path, 'exec')
        except SyntaxError as e:
            warnings.append(
                f"SYNTAX ERROR at line {e.lineno}: {e.msg}. "
                f"Common fix: use single quotes inside f-strings "
                f"(e.g., f\"{{bm['title']}}\" not f\"{{bm[\"title\"]}}\"). "
                f"Rewrite the file with correct syntax.")

    if ext == ".html":
        placeholders = ["Short bio", ">Name<", ">Role<",
                        "placeholder text", "Lorem ipsum",
                        ">Description<", ">Title<"]
        found = [p for p in placeholders if p.lower() in content.lower()]
        if found:
            warnings.append(
                f"Contains placeholder text: {', '.join(found)}. "
                f"Replace with realistic content.")

        has_placeholder_img = re.search(
            r'src=["\'][^"\']*placeholder[^"\']*["\']', content, re.IGNORECASE)
        if has_placeholder_img:
            warnings.append(
                "References nonexistent placeholder image. "
                "Use a CSS circle with initials instead.")

        if "fonts.googleapis" not in content and "fonts.google" not in content:
            warnings.append("No Google Fonts import detected.")

    elif ext == ".css":
        colors = re.findall(r'#[0-9a-fA-F]{3,6}', content)
        generic = {"#333", "#333333", "#666", "#666666", "#999",
                   "#fff", "#ffffff", "#f4f4f4", "#f5f5f5", "#f4f4f9",
                   "#eee", "#eeeeee", "#ddd", "#ccc", "#000", "#000000"}
        unique_colors = set(c.lower() for c in colors) - generic
        if len(unique_colors) == 0 and colors:
            warnings.append(
                "All colors are generic greys/whites. Use a real color palette.")

        if "transition" not in content:
            warnings.append("No CSS transitions found. Add for smooth hover effects.")

        if "padding" not in content:
            warnings.append("No padding found. Cards/sections need inner padding.")

    return warnings
