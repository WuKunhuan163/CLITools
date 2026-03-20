---
name: task-orchestration
description: How to decompose user requests into multi-tool workflows. Teaches agents to plan before executing, choose the right tools, and compose them into reliable sequences.
---

# Task Orchestration

## When to Use

Apply this skill whenever a user request involves:
- Multiple tools working together
- Sequential dependencies (step B needs output of step A)
- External services that can fail (APIs, browser sessions, network)
- Bulk operations (doing something for many items)

## Step 1: Decompose the Request

Break the user's request into atomic operations. Each operation should map to one tool or one function call.

**Template:**
```
User request: "<what they asked>"
Prerequisites: [what must be true before we start]
Steps:
  1. [tool/function] — [what it does] — [what could fail]
  2. [tool/function] — [what it does] — [what could fail]
  ...
Result: [what success looks like]
```

**Example:**
```
User request: "Send Happy New Year to all WhatsApp contacts"
Prerequisites: Chrome running with CDP port 9222, WhatsApp Web linked
Steps:
  1. WHATSAPP get_auth_state() — verify logged in — could be logged out
  2. WHATSAPP get_chats() — get contact list — page might not be loaded
  3. For each contact: WHATSAPP send_message(contact, text) — send message — rate limiting
Result: All contacts receive the message, report sent/failed counts
```

## Step 2: Identify Prerequisites

Before executing, check ALL prerequisites. Common ones:
- **CDMCP tools**: Chrome running? Tab open? Session authenticated? Use `open_tab()` from `logic/chrome/session.py` to create tabs automatically.
- **MCP tools**: API key configured? MCP server installed?
- **File tools**: Directory exists? Permissions correct?
- **Network tools**: Internet reachable? API endpoint responding?

**Critical**: Read `for_agent.md` for EACH involved tool AND its dependencies before writing any code. For CDMCP tools, also read:
- `logic/chrome/for_agent.md` (CDPSession, open_tab, find_tab)
- `tool/GOOGLE.CDMCP/logic/for_agent.md` (session management, rate limits)
- `SKILLS show recipes` (CDMCP Session Bootstrap recipe)

## Step 3: Plan Error Handling

For each step, plan what to do if it fails:

| Failure Type | Strategy |
|-------------|----------|
| Auth failure | Prompt user to log in, retry |
| Rate limit | Exponential backoff (1s, 2s, 4s, 8s...) |
| Network timeout | Retry 3 times with increasing timeout |
| Element not found | Wait and retry, then screenshot for debugging |
| Unknown error | Log error, skip item, continue with next |

## Step 4: Execute with Progress Tracking

For bulk operations:
1. Count total items
2. Track completed/failed/skipped counts
3. Report progress every N items or every 30 seconds
4. At the end, print a summary

## Step 5: Validate Results

After execution, verify the outcome:
- Did the expected number of operations succeed?
- Are there any partial failures to report?
- Does the user need to take any manual action?

## Execution Order

When receiving multiple tasks from the user:

**Default rule:** Fix tasks in the order they appear, unless:
1. The user explicitly specifies priority
2. A dependency exists (task B requires task A's output — do A first)
3. A task is blocked — skip and note the blocker in the brain

**Workflow:**
1. Record all tasks: `BRAIN add "..."` for each
2. Start with the first task in the order given
3. Complete each task before moving to the next
4. If blocked, note in brain and move to next unblocked task
5. After all tasks, `USERINPUT` to report completion

**Anti-pattern:** Cherry-picking easy tasks for quick progress. The user ordered them intentionally.

## Anti-Patterns

1. **No planning**: Jumping straight to tool calls without checking prerequisites
2. **No error handling**: Assuming every call succeeds
3. **No progress**: Running 100 operations silently with no feedback
4. **No validation**: Declaring success without checking results
5. **Sequential when parallel is possible**: Always check if operations are independent
6. **Working on multiple tasks simultaneously**: Partial progress on 5 tasks is worse than complete progress on 3

## Composing Tools

When multiple tools need to work together:

1. **Read each tool's `for_agent.md`** before starting
2. **Check for shared dependencies** (e.g., both need Chrome CDP)
3. **Establish session order** (boot CDMCP -> open tab -> authenticate -> operate)
4. **Pass data between tools** via return values or temporary files
5. **Clean up** sessions/resources when done

## Related Skills

- `recipes` — concrete multi-tool workflow examples
- `error-recovery-patterns` — retry, backoff, fallback strategies
- `preflight-checks` — validate prerequisites before execution
