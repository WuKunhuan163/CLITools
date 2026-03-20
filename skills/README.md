# skills/

AI agent skill documents organized as a dictionary hierarchy. Each directory level narrows the topic. Navigate down to find specific guidance; navigate up when the specific guidance doesn't cover your need.

## Structure

```
skills/
├── _/                # Foundational principles (modularization, symmetric design, meta-agent)
├── development/      # Building tools, commands, features (10 skills)
├── quality/          # Code health, auditing, deduplication (4 skills)
├── infrastructure/   # Runtime patterns: caching, display, error handling (8 skills)
├── workflow/         # Agent operations: onboarding, orchestration, self-improvement (6 skills)
├── browser/          # Browser automation and web exploration (2 skills)
├── IDE/              # IDE-specific skills (Cursor rules, settings)
└── clawhub/          # External marketplace skills
```

## How Skills Work

Skills are a **dictionary tree**. Each level has:
- `README.md` — What you'll find at this level
- `AGENT.md` — Navigation guide: what's below, what's above
- Subdirectories — either more categories or a `SKILL.md` at the leaf

This structure is itself informative. An agent looking for "how to write tests" navigates: `skills/` → `development/` → `unit-test-conventions/SKILL.md`. The path encodes the topic hierarchy.

## Commands

- `SKILLS list` — Browse all available skills
- `SKILLS show <name>` — View a skill's content
- `SKILLS sync` — Link skills to `~/.cursor/skills/` for Cursor integration

## Principles

The three foundational skills in `_/` govern all others:
1. **Modularization** — Every skill, like every module, has a single clear purpose
2. **Symmetric Design** — Skills follow a consistent format (frontmatter + sections)
3. **Meta-Agent** — Skills accumulate institutional knowledge that transfers between agents
