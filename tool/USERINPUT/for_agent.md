# USERINPUT - Agent Guide

## Quick Reference

| Command | Purpose |
|---------|---------|
| `USERINPUT` | Get user feedback (auto-claims from queue if available). |
| `USERINPUT --enquiry` | Bypass queue, request real-time user feedback. |
| `USERINPUT --enquiry --hint "question"` | Ask user a specific question, bypassing queue. |
| `USERINPUT --hint "context"` | Get feedback with context hint (may claim from queue). |
| `USERINPUT --queue` | Add a prompt to the queue via GUI. |
| `USERINPUT --queue --add "text"` | Add a prompt to the queue directly. |
| `USERINPUT --queue --delete <id>` | Delete a queued prompt by index. |
| `USERINPUT --queue --list` | List all queued prompts. |
| `USERINPUT --queue --gui` | Open queue manager GUI. |
| `USERINPUT --system-prompt --list` | List system prompts. |
| `USERINPUT --system-prompt --gui` | Manage system prompts via GUI. |
| `USERINPUT --system-prompt --add "rule"` | Add a system prompt. |
| `USERINPUT --system-prompt --delete <id>` | Remove a system prompt by index. |
| `USERINPUT --config` | Show current configuration values. |
| `USERINPUT --config --focus-interval 90` | Set refocus interval. |

## Queue Behavior

When `USERINPUT` is called without `--queue` and without `--enquiry`:
1. If the queue has items, the first item is claimed and returned as the result.
2. If the queue is empty, the normal GUI window opens for user input.

The output status reflects the source:
- **Normal input**: "Successfully received: ..."
- **From queue**: "Successfully received from queue (N remaining): ..."

## When to Use --enquiry

Use `--enquiry` when you need to ask the user a direct question during task execution. Without it, a queued prompt might be returned instead of the user's real-time answer, which could redirect you to a different task.

Typical scenarios:
- Asking for clarification on the current task.
- Confirming an approach before proceeding.
- Reporting an error and asking for guidance.

## System Prompt Management

System prompts are appended to every USERINPUT response. Manage them via `--system-prompt`:

```bash
USERINPUT --system-prompt --add "New rule"
USERINPUT --system-prompt --delete 0
USERINPUT --system-prompt --move-up 3
USERINPUT --system-prompt --list
USERINPUT --system-prompt --gui
```

## Configuration Management

Configuration values (non-prompt settings) are managed via `--config`:

```bash
USERINPUT --config                          # Show current config
USERINPUT --config --focus-interval 90      # Set refocus interval
USERINPUT --config --time-increment 60      # Set add-time increment
```

## Important Rules

1. USERINPUT is a **blocking** command. Never use `block_until_ms: 0`.
2. Execute USERINPUT at every workflow boundary.
3. Use `--hint` to explain why you are requesting feedback.
4. Use `--enquiry` when you need the user's real-time response, not a queued task.

## MCP Development

When developing MCP tools that automate web applications (CDMCP tools), refer to the `cdmcp-web-exploration` skill for systematic exploration and self-testing methodology.
