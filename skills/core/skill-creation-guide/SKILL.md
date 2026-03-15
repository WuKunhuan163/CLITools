---
name: skill-creation-guide
description: Guide for creating, managing, and organizing skills in the AITerminalTools project.
---

# Skill Creation Guide

## Overview

Skills are structured knowledge documents that AI agents read to follow project conventions. They live as `SKILL.md` files inside named directories.

## Directory Structure

```
/Applications/AITerminalTools/skills/
    core/                           # Framework-specific skills
        <topic>/
            SKILL.md
        openclaw/
            SKILL.md
            data/
                lessons.jsonl
    AI-IDE/
        Cursor/                     # Cursor IDE-specific skills
            <topic>/
                SKILL.md
```

## Creating a New Skill

1. Create the directory:
```bash
mkdir -p /Applications/AITerminalTools/skills/core/<topic>
```

2. Write `SKILL.md` with frontmatter:
```markdown
---
name: <topic>
description: One-line description.
---

# Title

Content here...
```

3. Sync to Cursor:
```bash
SKILLS sync
```

## Naming Convention

- Use kebab-case: `code-quality-review`
- No prefix needed -- the directory path provides context (`core/` vs `AI-IDE/Cursor/`)
- Be descriptive but concise

## Content Guidelines

### Progressive Disclosure (Required)

Skills use a three-level loading system to manage context efficiently:

1. **Metadata** (name + description in frontmatter): ~100 words, always in context. The description is the PRIMARY triggering mechanism — it determines when the skill gets used. Include BOTH what the skill does AND when to use it.

2. **SKILL.md body**: Loaded when the skill triggers. Keep under 500 lines. Core workflow, decision points, common mistakes, and pointers to bundled resources.

3. **Bundled resources** (optional): Loaded on demand when the agent needs specifics.

```
skill-name/
├── SKILL.md          ← Required. Frontmatter + body.
├── scripts/          ← Optional. Executable code for deterministic tasks.
├── references/       ← Optional. Detailed docs loaded on demand.
└── assets/           ← Optional. Files used in output (templates, etc.)
```

### Writing Quality Rubric

| Quality | Pattern | Example |
|---------|---------|---------|
| **Good** | Concrete example with correct and incorrect usage | "Good: `SKILLS learn \"Specific lesson\" --tool X`. Bad: `SKILLS learn \"Be careful\"`" |
| **Good** | Decision tree or rubric for judgment calls | "If mechanical → tool. If heuristic → skill." |
| **Good** | Anti-patterns section with WHY they're bad | "Anti-pattern: Monolithic SKILL.md. Why: wastes context tokens on irrelevant sections." |
| **Bad** | Vague advice without examples | "Write clear descriptions." |
| **Bad** | Only positive patterns, no warnings | Missing failure modes means the agent repeats known mistakes. |
| **Bad** | >500 lines in SKILL.md body | Split into references/ for detail. |

### Structure Template

```markdown
---
name: topic-name
description: What this skill covers. Use when [specific triggers].
---

# Title

## Why This Exists
Brief motivation (2-3 sentences). What problem does this solve?

## Core Workflow
Step-by-step with decision points and code examples.

## Concrete Examples
At least 2 good examples and 2 anti-patterns.

## Anti-Patterns
What NOT to do, with explanations.

## See Also
Links to related skills, tools, or docs.
```

### General Principles

- Start with a YAML frontmatter block (`name`, `description`)
- Use clear headings and code examples
- Reference other skills by name when relevant
- Keep actionable: tell the reader what to DO, not just what to KNOW
- Include positive AND negative examples (good/bad patterns)
- Prefer concrete examples over verbose explanations

## Storage Policy

All skills MUST live in the project directory:
```
/Applications/AITerminalTools/skills/
```

`~/.cursor/skills/` should only contain symlinks created by `SKILLS sync`. This ensures:
- Skills are version-controlled (git-tracked)
- New users get all institutional knowledge
- Deleting `.cursor/` doesn't destroy skills

## Symlink Safety

`SKILLS sync` creates symlinks: `~/.cursor/skills/<name>` -> `skills/<category>/<name>`.

WARNING: `rm -rf symlink/` (with trailing slash) follows through and deletes the TARGET contents. Always use `rm symlink` (no trailing slash) when removing symlinks. Since skills are tracked in git, accidental deletion can be recovered via `git checkout -- skills/`.
