"""Base ecosystem support — TOOL level.

Structural knowledge about the AITerminalTools project.
"""


def get_guidelines():
    return {
        "conventions": {},
        "ecosystem": {
            "architecture": [
                "Tool = tool/<NAME>/{main.py, logic/, interface/, hooks/, test/}.",
                "Shared code: logic/ (internal), interface/ (facade). Import from interface.*, never logic.* directly.",
                "Docs: README.md (usage), for_agent.md (agent internals), SKILL.md (best practices).",
                "Symmetric root directories: logic/, interface/, hooks/, test/, skills/, runtime/, data/.",
            ],
            "discovery": [
                "TOOL --search all 'query' — find anything (tools, skills, lessons).",
                "TOOL --search tools 'keyword' — find tools by capability.",
                "SKILLS show <name> — load a skill's full content.",
                "SKILLS list — show all skills and sync status.",
            ],
            "patterns": [
                "Turing machine: use ProgressTuringMachine for multi-stage progress display.",
                "Localization: use _() helper + TOOL --lang audit for multi-language support.",
                "Hooks: tool/<NAME>/hooks/{interface/, instance/, config.json} for event-driven extensions.",
                "Preflight: validate conditions before risky operations (from interface.utils import preflight).",
            ],
            "commands": [
                "Every tool name IS its command: GIT, PYTHON, SEARCH, LLM, SKILLS.",
                "Symmetric commands: TOOL_NAME --ask (read-only), --plan (design), --agent (autonomous).",
                "TOOL --dev create <NAME> — scaffold a new tool with full structure.",
                "TOOL --audit code — static analysis; TOOL --audit imports — dependency check.",
            ],
        },
    }
