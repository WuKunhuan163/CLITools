---
name: documentation-guide
description: How to write README.md and AGENT.md at each module level. Covers the distinction between user-facing and agent-facing docs, layered navigation for modular hierarchies, and interface documentation that enables context-free agents to embrace the ecosystem.
---

# Documentation Guide

Documentation in this ecosystem serves as a navigation system. Like road signs on a highway, each level's docs tell you what's ahead, what's beside you, and how to get where you need to go. Without them, even capable agents wander aimlessly through code.

## README.md vs AGENT.md

| Aspect | README.md | AGENT.md |
|--------|-----------|----------|
| **Audience** | Human developers, users | AI agents, assistants |
| **Tone** | Explanatory, user-friendly | Prescriptive, actionable |
| **Content** | What it does, how to use it, examples | How to work with it, rules, constraints, API surface |
| **Depth** | Enough to get started | Enough to operate autonomously |
| **Updates** | When features change | When agent behavior or interfaces change |

**README.md** answers: "What is this? How do I use it?"
**AGENT.md** answers: "What must I know to work here correctly?"

## Layered Navigation

This ecosystem is a modular hierarchy. Each layer has its own README.md and AGENT.md that serve as wayfinding markers:

```
/                           # Root: "Welcome to the ecosystem. Start here."
├── AGENT.md                # Agent bootstrap: architecture, conventions, commands
├── README.md               # User intro: what this is, how to install
├── logic/                  # Shared code layer
│   ├── AGENT.md            # "Here's what shared logic contains"
│   ├── brain/              # Brain subsystem
│   │   ├── AGENT.md        # "Brain manages tasks, sessions, experience"
│   │   └── instance/
│   │       └── AGENT.md    # "Sessions directory structure, migration rules"
│   └── utils/
│       └── AGENT.md        # "Available utilities: turing, resolve, cleanup..."
├── interface/
│   └── AGENT.md            # "Import from here, never from logic/ directly"
├── skills/
│   ├── README.md           # "Skills are a dictionary tree. Navigate by topic."
│   └── _/                  # Core skills
│       └── AGENT.md        # "Foundational development practices"
└── tool/
    └── PYTHON/
        ├── README.md       # "Manages standalone Python installations"
        └── AGENT.md        # "Commands, interface, known issues"
```

### The Navigation Contract

Each AGENT.md at a directory level must answer:
1. **What's in this directory?** — Brief inventory of subdirectories and their purpose.
2. **What should I do here?** — Common actions an agent would take at this level.
3. **Where should I go next?** — Pointers to deeper levels based on what the agent needs.
4. **What shouldn't I do?** — Constraints, common mistakes, rules.

Each README.md at a directory level must answer:
1. **What is this?** — One-paragraph explanation for a human unfamiliar with the project.
2. **How do I use it?** — Setup, commands, or code examples.
3. **What's inside?** — Directory listing with brief descriptions.

### The Context-Free Agent Test

Imagine an agent dropped into this ecosystem with no prior context. They read the root AGENT.md, which tells them about the tool architecture. They navigate to `logic/`, read its AGENT.md, which tells them about shared utilities. They follow the pointer to `logic/_/brain/AGENT.md`, which explains brain management.

At no point should the agent need to grep for information. The layered docs should guide them like a GPS — each turn reveals the next direction.

**If an agent reads all AGENT.md files on the path from root to their target and still doesn't know how to proceed, the documentation has failed.**

## Interface Documentation

Interface docs are the most critical documentation in the ecosystem. They are the contract that enables decoupled development.

### What an Interface AGENT.md Must Contain

```markdown
# tool/<NAME>/interface/ — Agent Guide

## Public API

### `function_name(param1: type, param2: type = default) -> ReturnType`
Brief description of what it does.

**Inputs:**
- `param1`: What this is, valid values, constraints
- `param2`: What this is, default behavior

**Returns:** What the return value represents.

**Raises:**
- `SomeError`: When this condition occurs

**Side Effects:** Any non-obvious behaviors (file creation, network calls, state changes).

**Example:**
\`\`\`python
from tool.NAME.interface.main import function_name
result = function_name("input", timeout=30)
\`\`\`

## Related Interfaces
- Upstream: What this interface depends on
- Downstream: What depends on this interface
```

### Change Propagation Rule

When you modify an interface function:
1. Update its own AGENT.md (signature, behavior, error conditions)
2. Run `TOOL --audit imports` to find all consumers
3. Update each consumer's AGENT.md if the change affects their behavior
4. Walk the dependency chain until changes no longer propagate

This is the documentation equivalent of ripple testing — a change at one level may require updates at every level downstream.

## Real Development Experience as Documentation

Skills and docs should reference real development experiences as concrete examples. This creates a feedback loop:

1. **Development happens** → encounters a problem or pattern
2. **Lesson is captured** → via `BRAIN log` or experience recording
3. **Documentation is updated** → with the real example
4. **Future agents learn** → from the concrete scenario, not abstract rules

### How Documentation and User-Experience Skills Complement Each Other

| documentation-guide | user-experience |
|---|---|
| Focuses on how to write README/AGENT.md | Focuses on what users see/experience |
| Covers the navigation system for agents | Covers the accessibility of features for users |
| Interface documentation standards | CLI bridge patterns for deep logic |
| The "what to write" | The "why to write it" |

To avoid duplication between these skills:
- **documentation-guide** owns the format, structure, and navigation contract
- **user-experience** owns the UX principle: why documentation placement matters, what users should be able to find

When referencing real development experiences:
- **documentation-guide** cites the experience as an example of how to document
- **user-experience** cites the same experience as an example of how to design accessibility

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
|-------------|-------------|-----|
| No AGENT.md at module level | Agents can't discover the module's purpose | Always create AGENT.md when creating a directory |
| AGENT.md that just says "see code" | Defeats the purpose of documentation | Describe purpose, API, constraints |
| README.md with implementation details | Users don't need to know internals | Keep README user-focused |
| Interface without documented error cases | Consumers can't handle failures | Document every exception and edge case |
| Updating code without updating docs | Docs become lies, agents make mistakes | Update docs in the same commit as code |
| Monolithic AGENT.md at root | Too much info at one level | Push details down to appropriate levels |
| Abstract rules without real examples | Agents can't generalize from theory | Always include a concrete scenario |

## The `TOOL --audit skills` Check

`TOOL --audit skills` verifies that every directory level in the skills hierarchy has both README.md and AGENT.md. This same principle should extend to all module directories — use the audit as a model.
