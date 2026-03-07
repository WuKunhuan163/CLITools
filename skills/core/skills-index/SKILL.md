---
name: skills-index
description: Index of all available AITerminalTools skills organized by category. Use as a starting point to discover relevant development guides.
---

# Skills Index

## How to Use

```bash
SKILLS list              # List all skills and their sync status
SKILLS show <name>       # Display a skill's content
SKILLS sync              # Sync project skills to Cursor
```

---

## Development Workflow

How to build, structure, and extend tools.

| Skill | Purpose |
|-------|---------|
| `tool-development-workflow` | Complete tool creation lifecycle |
| `standard-command-development` | Three-layer architecture (CLI, Logic, Interface) |
| `tool-interface` | Cross-tool public API via `interface/main.py` |

## Conventions & Style

Project-wide naming and coding conventions.

| Skill | Purpose |
|-------|---------|
| `naming-conventions` | Tool names, CLI subcommands, file/variable naming rules |

## Quality & Testing

Ensuring correctness, consistency, and coverage.

| Skill | Purpose |
|-------|---------|
| `code-quality-review` | Import rules (IMP001-IMP004), audits, static analysis |
| `unit-test-conventions` | Test file naming, structure, sequential execution |
| `tmp-test-script` | Temporary scripts in `tmp/` for quick verification |
| `exploratory-testing` | Systematic exploration of unknown APIs/protocols |
| `avoid-duplicate-implementations` | Search before implementing, extend over duplicate |

## Framework Infrastructure

Internal systems powering the framework.

| Skill | Purpose |
|-------|---------|
| `localization` | Multi-language `_()` helper, translation files, audits |
| `record-cache` | Caching patterns, `data/` directory conventions |
| `retention-rotation` | Limit + delete-half strategy for logs, caches, and files |
| `session-debug-log` | `tool.log()`, SessionLogger, debug file techniques |
| `setup-tutorial-creation` | TutorialWindow multi-step GUI wizards |
| `turing-machine-development` | TuringStage, progress pipelines, parallel workers |

## MCP & Browser Automation

Building CDMCP tools for web applications.

| Skill | Purpose |
|-------|---------|
| `mcp-development` | Session management, overlays, auth-gated commands |
| `cdmcp-web-exploration` | DOM exploration, selector discovery, page automation |

## Self-Improvement

The OpenClaw feedback loop: error -> lesson -> rule -> skill -> hook.

| Skill | Purpose |
|-------|---------|
| `openclaw` | Complete self-improvement workflow with lessons and hooks |
| `development-report` | Writing structured development session reports |

## Meta

Skills about managing skills.

| Skill | Purpose |
|-------|---------|
| `skill-creation-guide` | Conventions for creating, naming, and storing skills |
| `skills-index` | This file |

## Cursor IDE

Cursor-specific skills (under `AI-IDE/Cursor/`).

| Skill | Purpose |
|-------|---------|
| `Cursor-create-rule` | Creating `.cursor/rules/*.mdc` files |
| `Cursor-create-skill` | Comprehensive guide for authoring Cursor skills |
| `Cursor-create-subagent` | Custom subagents with cost control policy |
| `Cursor-migrate-to-skills` | Converting rules/commands to skill format |
| `Cursor-update-cursor-settings` | Modifying `settings.json` preferences |
