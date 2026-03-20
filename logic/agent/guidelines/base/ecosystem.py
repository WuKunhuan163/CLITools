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
                "Docs: README.md (usage), for_agent.md (agent internals), for_agent_reflection.md (self-improvement), SKILL.md (best practices).",
                "Every directory has README.md + for_agent.md forming a layered hierarchy: root → logic/<module>/ → tool/<NAME>/.",
                "Symmetric root directories: logic/, interface/, hooks/, test/, skills/, runtime/, data/.",
            ],
            "discovery": [
                "TOOL --eco search 'query' — find anything (tools, skills, lessons, docs).",
                "TOOL --eco tool <NAME> — deep-dive into a specific tool.",
                "TOOL --eco skill <name> — read a development skill/pattern.",
                "TOOL --eco guide — onboarding for new agents.",
                "TOOL --eco map — ecosystem directory structure.",
                "TOOL --eco cmds — blueprint shortcut commands.",
                "OPENCLAW --status — self-improvement dashboard.",
                "OPENCLAW --audit — check for unprocessed lessons needing skill creation.",
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
