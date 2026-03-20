---
name: source-exploration
description: How agents should explore an unfamiliar codebase, discover tools, interfaces, and skills using semantic search. The first step in any development task.
---

# Source Exploration

## When to Use

Before modifying any code, before creating any new file, before writing any tool:

1. You received a task that touches code you haven't read yet
2. You're about to create something new (tool, interface, utility)
3. You need to understand how an existing system works

## The Exploration Sequence

### Step 1: Search for existing tools

```bash
# Natural language — describe what you need
TOOL --search tools "download photos from cloud"
TOOL --search tools "send messages to users"
TOOL --search tools "execute shell commands safely"
```

What this tells you:
- Whether a tool already exists for the task
- Which tools are related (might have reusable logic)
- Which tools have README/for_agent docs (read those first)

### Step 2: Search for existing interfaces

```bash
# Before writing any cross-tool code
TOOL --search interfaces "rate limiting for API calls"
TOOL --search interfaces "run subprocess with timeout"
TOOL --search interfaces "manage background process"
```

Why: An interface might already expose exactly what you need. Using it
means zero duplication and automatic compatibility with future changes.

### Step 3: Search for relevant skills

```bash
# Global skill search
SKILLS search "how to handle Chrome sessions"

# Tool-scoped search (also includes global skills)
GIT --skills search "persist data across branches"
```

Why: Skills contain battle-tested patterns. Following them avoids
re-discovering solutions that the project already knows.

### Step 4: Check lessons

```bash
SKILLS lessons --tool TOOL_NAME
SKILLS lessons --last 30
```

Why: Past agents hit real bugs. Their lessons prevent you from
repeating the same mistakes.

## Reading Order for a Tool

When you've identified a relevant tool:

1. `tool/<NAME>/README.md` — Overview, setup, usage
2. `tool/<NAME>/AGENT.md` — Agent-specific rules and API surface
3. `tool/<NAME>/interface/main.py` — Public API (what you can import)
4. `tool/<NAME>/tool.json` — Dependencies and metadata
5. `tool/<NAME>/skills/` — Tool-specific skills (if any)

Do NOT read `logic/` files unless you're modifying the tool itself.
The interface is the contract; internals are implementation details.

## Concrete Example

**Task**: "Help me send a WhatsApp message."

```bash
# Step 1: Find the tool
TOOL --search tools "send WhatsApp message"
# → WHATSAPP (17%), GMAIL (14%), DINGTALK (7%)

# Step 2: Read its docs
# Read tool/WHATSAPP/README.md
# Read tool/WHATSAPP/AGENT.md

# Step 3: Check for interfaces
TOOL --search interfaces "send message"
# → WHATSAPP interface, DINGTALK interface

# Step 4: Check lessons
SKILLS lessons --tool WHATSAPP
# → "WhatsApp enforces 20msg/min rate limit"

# Now you have full context to proceed safely
```

## Anti-Patterns

- **Diving into code without searching**: You'll create duplicate tools
  or miss existing interfaces.
- **Reading all source files sequentially**: Token-wasteful. Use
  semantic search to find what matters.
- **Ignoring `AGENT.md`**: This file exists specifically for you.
  It contains rules that prevent common agent mistakes.
- **Creating a new utility without checking interfaces**: Run
  `TOOL --search interfaces` first. Always.
