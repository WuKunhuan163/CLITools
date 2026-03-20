# Agent Instructions

This project is an AI-native tool ecosystem. Read [`for_agent.md`](for_agent.md) Section 0 before doing anything.

## Bootstrap (mandatory)

1. Read `runtime/brain/context.md` if it exists — it has the previous session's state and current tasks.
2. Run `TOOL status` to see installed tools.
3. Run `TOOL --eco search "your task keywords"` before writing any code.
4. After each task: run `USERINPUT --hint "summary"` to report to the user.

## Key Commands

All commands are shell commands — run them in the terminal:

| Command | Purpose |
|---|---|
| `TOOL status` | See all tools and installation status |
| `TOOL --eco search "query"` | Find anything (tools, skills, lessons, docs) |
| `TOOL --eco nav [path]` | Browse skills dictionary tree (like `cd` + `ls`) |
| `TOOL --eco tree` | Full skills tree structure |
| `TOOL --eco skill <name>` | Read a development skill |
| `TOOL --eco guide` | Full onboarding walkthrough |
| `USERINPUT --hint "summary"` | Report to user (blocking) |
| `BRAIN add/done/list` | Manage tasks |
| `BRAIN reflect` | Self-check protocol |
| `SKILLS learn "lesson"` | Record a discovery |

## Architecture

- **Symmetric**: every tool has the same structure (`main.py`, `logic/`, `interface/`, `tool.json`)
- **Layered**: entry → logic → interface. Import from `interface.*`, never `logic.*` directly.
- **Documented**: every directory has `README.md` (users) and `for_agent.md` (agents)
- **Skills as dictionary tree**: browse `skills/` like a filesystem with `TOOL --eco nav`

## Foundational Skills

Before architectural decisions, read these:

- `TOOL --eco skill modularization` — decomposition and anti-patterns
- `TOOL --eco skill symmetric-design` — consistent structure reduces entropy
- `TOOL --eco skill meta-agent` — self-iteration and knowledge pipeline

## Full Guide

See [`for_agent.md`](for_agent.md) for the complete agent guide (1000+ lines).
