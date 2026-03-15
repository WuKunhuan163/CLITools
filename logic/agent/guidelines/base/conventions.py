"""Base development conventions — TOOL level.

These apply to ALL agents regardless of scope.
OPENCLAW and other layers extend these via layers/*.py.
"""


def get_guidelines():
    return {
        "conventions": {
            "experience": [
                "Record discoveries and gotchas via experience() or SKILLS learn after each non-obvious finding.",
                "Update runtime/brain/tasks.md after completing tasks; mark done, add new ones.",
                "Update runtime/brain/context.md with current work state so the next session can resume.",
                "Runtime is a symmetric directory — each tool can have its own runtime/brain/ for tool-specific context.",
            ],
            "exploration": [
                "Before implementing: search for existing skills/tools via TOOL --search all 'query'.",
                "Read for_agent.md for tool internals before extending or debugging a tool.",
                "Use SKILLS show <name> to load relevant skills; check skills-index for the master list.",
                "Prefer extending existing implementations over creating new ones (avoid-duplicate-implementations).",
            ],
            "quality": [
                "Fix bugs directly in source — don't work around them.",
                "Update README.md and for_agent.md after structural changes.",
                "Run TOOL --audit code and TOOL --lang audit to verify quality.",
                "Use tmp/ scripts for exploratory testing before committing changes.",
            ],
            "infrastructure": [
                "Repeated lessons (3+) on the same theme should become a skill.",
                "Mechanical processes described in skills should become automated functions.",
                "New root-level directories require .gitignore exceptions (deny-by-default pattern).",
                "Imports from tool.X.interface → declare in tool.json dependencies.",
            ],
        },
        "ecosystem": {},
    }
