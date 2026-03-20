---
name: skill-formation
description: When and how to create new skills from accumulated experience. Covers the criteria for skill creation, content structure, placement decisions, and validation.
---

# Skill Formation

## When to Create a Skill

Create a new skill when ALL conditions are met:

1. **3+ lessons** cluster around the same topic
2. The knowledge is **judgment-based** (not purely mechanical)
3. The pattern will **recur** in future work
4. No existing skill already covers it (search first!)

```bash
# Always search before creating
SKILLS search "the topic you want to skill-ify"
TOOL --search skills "the topic"
```

## Where to Place It

| Scope | Location | Example |
|-------|----------|---------|
| Cross-tool, foundational | `skills/core/<name>/` | `record-cache`, `localization` |
| Specific to one tool | `tool/<TOOL>/skills/<name>/` | `tool/OPENCLAW/skills/memory-recall` |
| IDE-specific conventions | `skills/IDE/<IDE>/` | `skills/IDE/Cursor/` |

Rule of thumb: If the skill mentions a specific tool more than 3 times,
it belongs in that tool's skills directory.

## Skill Structure

```
<skill-name>/
├── SKILL.md          # Core guidance (< 500 lines)
├── scripts/          # Optional: automatable parts
│   └── check_x.py
└── references/       # Optional: tables, data
    └── patterns.md
```

### SKILL.md Frontmatter (required)

```yaml
---
name: skill-name
description: One-line description of when to use this skill.
---
```

### SKILL.md Body

1. **Why this exists** — what problem recurring agents face
2. **When to use** — triggers that should make the agent read this
3. **Core workflow** — the main decision tree or procedure
4. **Examples** — concrete, real examples from the project
5. **Anti-patterns** — what NOT to do (equally important)

## Content Quality Standards

### Keep it actionable

Every section should answer: "What should the agent DO differently?"

Bad: "Rate limiting is important for API stability."
Good: "Before any API call loop, check `SKILLS lessons --tool LLM`
for known rate limits. Use `retry_on_transient()` from the LLM
interface for automatic backoff."

### Use project vocabulary

Reference actual tool names, interface functions, and file paths:

Bad: "Use the caching system"
Good: "Use `AuditManager` from `logic/config/audit_manager.py` for
result caching (see `record-cache` skill)"

### Progressive disclosure

SKILL.md body: High-level guidance and decision trees.
scripts/: Executable, deterministic steps.
references/: Lookup tables, API references, detailed specs.

## Validation

After creating a skill, verify it's discoverable:

```bash
# Can agents find it?
SKILLS search "keywords from your skill description"

# Is it linked to Cursor?
SKILLS sync

# Does it show in tool-scoped search?
TOOL_NAME --skills search "keywords"
```

## Example: Creating a Skill from Lessons

### Input: 4 lessons about git binary resolution

```
1. "APFS case-insensitivity shadows git binary" (critical)
2. "Use get_system_git() not /usr/bin/git" (warning)
3. "shutil.which finds shadowed binary on macOS" (warning)
4. "All tools should use _git_bin() helper" (info)
```

### Output: Decision

These are all about the same pattern (git binary resolution),
they're cross-tool (affects GIT, USERINPUT, PYTHON, FONT), and
they involve judgment (knowing WHEN to use the helper). This
justifies a skill, not just a for_agent.md rule.

But wait — the fix is also mechanical (replace hardcoded path with
helper call). So the skill should include a script:

```
cross-tool-binaries/
├── SKILL.md          # When/why to use helper functions for binaries
├── scripts/
│   └── audit_hardcoded_paths.py  # Find remaining hardcoded paths
└── references/
    └── binary-resolution.md      # Platform-specific path lookup rules
```

## Anti-Patterns

- **Creating skills for one-off tasks**: Skills are for recurring
  patterns. One-off procedures belong in README or documentation.
- **500+ line SKILL.md**: Split into scripts/ and references/. The
  body should be guidance, not a manual.
- **Skill that duplicates a tool's for_agent.md**: If it's only
  relevant to one tool, extend for_agent.md instead.
- **Creating a skill without checking lessons first**: Skills should
  emerge FROM lessons, not be imagined from scratch.
