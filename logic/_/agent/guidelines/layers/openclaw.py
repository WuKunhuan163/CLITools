"""OPENCLAW layer — self-improvement loop guidelines.

Extends TOOL-level conventions with the OpenClaw loop:
  Error → Lesson → Skill → Tool → Hook enforcement.
"""


def get_guidelines():
    return {
        "conventions": {
            "experience": [
                "Error → Lesson: every unexpected failure must be recorded with severity classification.",
                "Lesson → Skill: after 3+ lessons on the same theme, synthesize into a reusable skill.",
                "Skill → Tool: mechanical skills (repeatable, checklistable) should become automated tools.",
                "Tool → Hook: new tools should expose hooks for pre/post event handling.",
            ],
            "self_improvement": [
                "Run self-audit after major changes: check for new lessons to capture.",
                "Review skills-index periodically for outdated or redundant skills.",
                "Propose infrastructure upgrades when manual patterns become repetitive.",
                "Feed lessons back into guidelines layers to close the loop.",
            ],
            "quality": [
                "Pre-commit hooks must pass before any commit (severity: BLOCK).",
                "Lessons with severity=BLOCK must become automated checks within one session.",
            ],
        },
        "ecosystem": {
            "patterns": [
                "OpenClaw loop: Error → Lesson → Rule → Skill → Hook enforcement.",
                "Lesson store: runtime/experience/lessons.jsonl — append-only, severity-classified.",
                "Skill creation: SKILLS create <name> — generates SKILL.md in skills/core/.",
                "Hook enforcement: hooks/instance/ — lifecycle hooks that enforce learned rules.",
            ],
            "discovery": [
                "OPENCLAW --status — self-improvement dashboard.",
                "OPENCLAW --audit — check for unprocessed lessons needing skill creation.",
            ],
        },
    }
