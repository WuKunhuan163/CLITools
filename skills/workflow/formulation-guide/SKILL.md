---
name: formulation-guide
description: Decision framework for creating new Skills vs new Tools when codifying recurring patterns. Use when you've identified something the project should "know" or "do" permanently and need to decide the right artifact. Covers the full lifecycle from pattern recognition through implementation.
---

# Formulation Guide: Skill vs Tool vs Script

## The Problem This Solves

Agents encounter recurring patterns. Without codification, each session re-discovers the same solutions. But choosing the wrong artifact wastes effort:

- A **skill** for something mechanical → agent re-interprets it every time instead of running a script
- A **tool** for something heuristic → rigid automation mishandles edge cases
- A **script** that should be a tool → no CLI entry point, no setup, no discoverability

## Decision Framework

### Step 1: Characterize the pattern

Ask: "If I had to explain this to another agent, would I describe **what to think about** or **what to execute**?"

| Signal | Points to... |
|--------|-------------|
| "It depends on the situation" | **Skill** — guidance, not automation |
| "Do these exact steps every time" | **Tool or script** — automation |
| "Usually X, but sometimes Y" | **Skill with scripts/** — hybrid |
| "Just run this one command" | **Script** inside existing skill or tool |

### Step 2: Apply the decision tree

```
Is the pattern the same sequence every time, with no judgment needed?
│
├── YES: Is it a self-contained workflow with inputs/outputs?
│   ├── YES: Does it need a CLI entry point, setup, or dependencies?
│   │   ├── YES → CREATE A TOOL (main.py, setup.py, tool.json)
│   │   └── NO  → ADD A SCRIPT to an existing skill or tool
│   └── NO: Is it a helper used by other code?
│       └── YES → ADD TO logic/ (shared utility)
│
└── NO: Does it require understanding context to apply correctly?
    ├── YES: Is the knowledge cross-cutting (applies to many tools)?
    │   ├── YES → CREATE A SKILL in skills/core/
    │   └── NO  → ADD TO the tool's AGENT.md
    └── NO: Is it a checklist or reference table?
        └── YES → ADD TO a skill's references/ directory
```

## Concrete Examples

### Example 1: "I keep writing the same iCloud download script"

**Pattern**: Every time user asks to download photos, agent writes a Python script that calls iCloud API, handles auth, manages parallel downloads.

**Decision**: This is mechanical, self-contained, needs CLI entry point → **Tool**.

Result: `tool/iCloud.iCloudPD/` with `main.py`, `setup.py`, `tool.json`.

Why NOT a skill: A skill would describe *how* to write the download script. But the script is the same every time — codify the script itself.

### Example 2: "CDMCP sessions keep breaking in different ways"

**Pattern**: Agents hit CDMCP failures (stale sessions, missing tabs, Chrome crashes) and each time discover the fix through trial and error.

**Decision**: Failures vary by context, fixes require judgment → **Skill**.

Result: `skills/core/mcp-development/SKILL.md` with session management patterns, common failure modes, recovery strategies.

Why NOT a tool: You can't automate "understand why the session broke." The agent needs to read the situation and apply the right fix.

### Example 3: "Font analysis needs both heuristic rules and deterministic scripts"

**Pattern**: Identifying fonts in images requires judgment (is this serif? what context?), but rendering test sheets and computing metrics is mechanical.

**Decision**: Hybrid — judgment + automation → **Skill with scripts/**.

```
font-analysis/
├── SKILL.md          ← When to use each technique, how to interpret results
├── scripts/
│   ├── render_test.py   ← Deterministic: render font comparison sheets
│   └── compute_metrics.py ← Deterministic: calculate font metrics
└── references/
    └── font-families.md  ← Reference: common font family characteristics
```

### Example 4: "Every API has rate limits, but handling them differs"

**Pattern**: Rate limit strategies depend on the API (fixed window, sliding window, token bucket) and the use case (batch processing, real-time, interactive).

**Decision**: Context-dependent, cross-cutting → **Skill** in `skills/core/`.

Why NOT a tool: Rate limit handling is woven into other code, not a standalone workflow.

### Example 5: "I need to rotate PDFs sometimes"

**Pattern**: Agent occasionally needs to rotate PDF pages. The code is 15 lines of PyMuPDF.

**Decision**: Too small for a tool, too mechanical for a skill body → **Script** in an existing skill.

Add `scripts/rotate_pdf.py` to a `pdf-processing` skill, not a new tool.

## What Goes in Each Artifact

### Skill SKILL.md body (< 500 lines)

- **When to use** this knowledge (triggers)
- **Core workflow** with decision points
- **Common mistakes** (anti-patterns)
- **Pointers** to scripts/ and references/ for details

Do NOT put in SKILL.md:
- Implementation code longer than 10 lines (→ scripts/)
- Reference data or tables (→ references/)
- Setup instructions (→ README.md in the skill dir, or link to tool)

### Tool main.py

- CLI argument parsing
- Error handling with clear messages
- Progress display for long operations
- Integration with project infrastructure (ToolBase, setup_paths)

### Script in scripts/

- Self-contained, executable
- Clear input/output contract
- Can be run without reading into context (token-efficient)

## Promotion Signals

How to know it's time to formulate:

| Signal | Count | Action |
|--------|-------|--------|
| Same lesson recorded | 3+ times | Consolidate into **AGENT.md rule** |
| Same script written | 3+ times | Wrap into **scripts/** or **tool** |
| Same multi-step judgment | 3+ times | Write a **skill** |
| Rule in AGENT.md growing | >10 lines | Extract into **skill** |
| Skill body growing | >500 lines | Split into **skill + references/** |
| Skill has >3 scripts | — | Consider promoting to **tool** |

## After Creating the Artifact

1. **Record why**: `SKILLS learn "Created <skill|tool> for <pattern> because <3+ occurrences>" --tool OPENCLAW`
2. **Link it**: Add cross-references from related skills/tools
3. **Test it**: Use the artifact on the next occurrence of the pattern
4. **Iterate**: First version is never final — update after real usage

## Anti-Patterns

- **Creating a tool for variable tasks**: If the task changes based on context, a tool will either be too rigid or too complex. Use a skill.
- **Writing a 200-line SKILL.md**: Progressive disclosure — keep SKILL.md lean, put details in references/.
- **Creating both a skill AND a tool for the same thing**: Pick the dominant mode. If it's 80% mechanical, make a tool with a brief AGENT.md. If 80% judgment, make a skill with scripts/.
- **Formulating too early**: Wait for 3 occurrences. One-off patterns don't need codification.
- **Never formulating**: If you're writing the same lesson for the 4th time, stop and create the artifact.
