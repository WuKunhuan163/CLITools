# skills/

AI agent skill documents — structured best-practice guides that agents reference during development.

## Structure

- `core/` — Core framework skills (tool development, testing, debugging patterns).
- `IDE/Cursor/` — Cursor IDE-specific skills (rule creation, subagent policies).
- `marketplace/` — Skills downloaded from external sources (ClawHub, OpenClaw, etc.).

## Format

Each skill is a directory containing at minimum a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name
description: Brief description for search and agent activation.
---
```

## Commands

- `SKILLS list` — Browse all available skills.
- `SKILLS show <name>` — View a skill's content.
- `SKILLS sync` — Link skills to `~/.cursor/skills/` for Cursor integration.
- `SKILLS market clawhub browse` — Browse marketplace skills.
- `SKILLS market clawhub install <slug>` — Download a skill from the marketplace.
