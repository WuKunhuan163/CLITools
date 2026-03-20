---
name: openclaw
description: OpenClaw-inspired self-improvement loop. Error -> Lesson -> Rule -> Skill -> Hook enforcement. Covers lesson capture, severity classification, quality standards, pre-commit hooks, and institutional memory.
---

# OpenClaw Self-Improvement Loop

## Core Principle

Every mistake becomes institutional memory. Zero regressions through escalating enforcement:

```
Error -> Fix -> Lesson -> Rule -> Skill -> Hook
```

## Data Architecture

Brain logic lives in the SKILLS tool; brain data lives in `runtime/_/eco/experience/` (a symmetric root directory):

```
tool/SKILLS/                         runtime/_/eco/experience/
├── main.py       (CLI entry)        ├── lessons.jsonl      (lesson log)
└── logic/                           ├── suggestions.jsonl  (improvement suggestions)
    └── evolution.py (brain logic)   └── evolution.jsonl    (applied changes history)
```

`runtime/` is a **symmetric root directory** — tracked by Git, unlike `data/` which is transient.

## Step 1: Capture Lessons

After fixing a non-trivial bug (took > 1 attempt), discovering a cross-module gotcha, or encountering user-reported unexpected behavior:

```bash
SKILLS learn "Description" --tool TOOL_NAME --severity warning --context "Context"
```

Lessons are appended to `runtime/_/eco/experience/lessons.jsonl`.

### Severity Guide

| Level | When | Example |
|-------|------|---------|
| `info` | Convention or best practice | "Always use `_` prefix for private functions" |
| `warning` | Bug-prone pattern | "Cross-process in-memory state is not shared" |
| `critical` | Data loss, security, breakage | "rm -rf symlink/ with trailing slash destroys target" |

### Lesson Categories

| Category | Example |
|----------|---------|
| Architecture | "Cross-process state requires file persistence, not in-memory" |
| API Behavior | "Google ListAccounts returns 200 even when not authenticated" |
| Timing | "Chrome tab creation is async; always wait for load event" |
| UI/UX | "Overlay injection must happen after DOMContentLoaded" |
| Recovery | "Session full_reboot must recreate both welcome and demo tabs" |

### Lesson Quality

Good lessons are:
- **Specific**: "Never call `_update_auth_state` from CLI process -- it only updates in-memory state"
- **Actionable**: Include what TO DO, not just what NOT to do
- **Contextual**: Reference the file/function where the lesson applies

Bad: "Be more careful", "Test better", "Fix the bug"

### When NOT to Capture

- Typos or trivial one-line fixes
- External API changes outside our control
- One-off configuration issues

## Step 2: Review Lessons

```bash
SKILLS lessons --last 20
SKILLS lessons --tool GOOGLE.CDMCP
```

## Step 3: Analyze Patterns

```bash
SKILLS analyze --days 30           # Full analysis
SKILLS analyze --tool GOOGLE.CDMCP # Tool-specific
```

Identifies recurring tools, severity clusters, and keyword patterns.

## Step 4: Get Improvement Suggestions

```bash
SKILLS suggest                     # All suggestions
SKILLS suggest --focus security    # Focused area
```

Generates typed suggestions (rule, hook, skill) with confidence scores.

## Step 5: Apply Suggestions

```bash
SKILLS apply <suggestion-id>       # Shows detail + action guide
SKILLS history                     # View applied changes
```

Each suggestion includes a concrete Action Guide with implementation steps.

## Step 6: Pattern Recognition -> Rule

When multiple lessons cluster around a theme, consolidate:
- **Workspace rules**: `.cursor/rules/*.mdc` (auto-loaded by Cursor)
- **Tool-specific rules**: `tool/<NAME>/AGENT.md`

## Step 7: Escalate to Skills

When a topic has enough rules for a coherent guide:

```bash
mkdir -p skills/core/<topic>
# Write SKILL.md
SKILLS sync
```

## Step 8: Enforce via Hooks

Automated pre-commit checks -- the highest form of a lesson:

```
tool/<NAME>/hooks/
    pre_commit.py       # Runs before git commit
    rules.json          # Machine-readable rules
```

### Hook Structure

```python
#!/usr/bin/env python3
"""Pre-commit hook: enforce learned rules for <TOOL>."""

def check_rule_name(files):
    """Rule: Description (lesson #N)."""
    errors = []
    for f in files:
        # Check for violation pattern
        ...
    return errors

def main():
    import subprocess
    result = subprocess.run(["git", "diff", "--cached", "--name-only"],
                          capture_output=True, text=True)
    changed = [f for f in result.stdout.strip().split("\n")
               if f.startswith("tool/<NAME>/")]
    if not changed:
        return 0
    errors = []
    errors.extend(check_rule_name(changed))
    if errors:
        for e in errors:
            print(f"  [HOOK] {e}")
        return 1
    return 0
```

## JSONL Entry Format

```json
{
  "ts": "2026-03-05T21:41:00",
  "lesson": "Description of the lesson",
  "severity": "warning",
  "tool": "GOOGLE.CDMCP",
  "context": "What caused this lesson"
}
```

## Portability

All skills live in `skills/`, brain data in `runtime/_/eco/experience/`. Both are Git-tracked. Never store institutional knowledge only in `~/.cursor/`. This ensures:
- New users get the same institutional knowledge
- Skills and brain data are version-controlled
- The agent's experience is portable across machines

## Marketplace

Browse and install community skills from ClawHub (3000+ skills):

```bash
SKILLS market browse                    # Top downloaded skills
SKILLS market search "cursor"           # Search by keyword
SKILLS market install <slug>            # Install to skills/marketplace/<source>/
SKILLS market installed                 # List installed marketplace skills
SKILLS market uninstall <slug>          # Remove a marketplace skill
```

Installed marketplace skills appear in `SKILLS list` and can be synced to Cursor via `SKILLS sync`.

## See Also

- `task-orchestration` — How to decompose requests into multi-tool workflows
- `error-recovery-patterns` — Retry, backoff, and failure handling strategies
- `preflight-checks` — Pre-flight validation and guard rails for risky operations
- `recipes` — End-to-end worked examples for common multi-tool tasks
- `skill-creation-guide` — How to create new skills
- `development-report` — Writing session reports
