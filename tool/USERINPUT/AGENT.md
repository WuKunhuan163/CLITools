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
| `USERINPUT --auto-commit-message "msg"` | Append a custom message to the auto-commit. |
| `USERINPUT --config` | Show current configuration values. |
| `USERINPUT --config --focus-interval 90` | Set refocus interval. |
| `USERINPUT --config --hook --start-after 500` | Set tool call threshold before reminders ramp up. |

## CRITICAL: Execution Requirements

### Pre-Operations Take Time

USERINPUT performs several automated operations **before** collecting user input:

1. **Git auto-commit** — stages, commits, and pushes all changes (30-60s)
2. **History maintenance** — git log compaction and history pruning
3. **LFS pruning** — cleans up large file storage objects
4. **Remote backup** — pushes to remote repository
5. **GUI window launch** — opens the input window with retry logic

These operations can take **30-120 seconds** depending on repository size and
network speed. This is why the command takes time before the input prompt appears.

### NEVER Use Short Timeouts

The default timeout is **300 seconds** (5 minutes). This is the minimum acceptable
value. NEVER set `--timeout` below the default.

```bash
# CORRECT — default timeout (300s)
USERINPUT

# CORRECT — explicit longer timeout
USERINPUT --timeout 600

# WRONG — too short, will timeout during git save
USERINPUT --timeout 30
USERINPUT --timeout 60
USERINPUT --timeout 120
```

### ALWAYS Use Blocking Execution

When calling USERINPUT from a Cursor agent or any orchestration:

- Set `block_until_ms` to **at least 310000** (310 seconds)
- NEVER use `block_until_ms: 0` (background execution)
- NEVER use `&` or `2>&1 &` to background the command
- NEVER use `nohup` or any detach mechanism

The command MUST run in the foreground and block until completion. Background
execution will cause the git save and GUI to run without being monitored, and
you will never see the user's response.

```
# CORRECT — blocking with sufficient timeout
block_until_ms: 310000

# WRONG — will background immediately, losing all output
block_until_ms: 0
block_until_ms: 5000
command: "python3 tool/USERINPUT/main.py 2>&1 &"
```

### Retry on Timeout/Empty

If USERINPUT times out or returns empty:

1. Sleep **30 seconds** (not 10)
2. Retry USERINPUT (without reducing timeout)
3. If still empty, sleep **60 seconds** and retry
4. Use exponential backoff: 30s, 60s, 120s
5. NEVER end your turn without at least one USERINPUT attempt

### Output Format

The output starts with the auto-save progress indicators (shown as Turing machine
stages), followed by the user's response, then system prompt and feedback directive:

```
正在保存进度...
正在维护历史...
正在备份到远端...
Pruning LFS objects...
Launching input GUI...
正在通过 GUI 等待 USERINPUT 反馈 (PID: 12345)(30s)...
成功接收: <user's response here>

系统提示 / System Prompt
0. <system prompt rule 0>
1. <system prompt rule 1>
...

关键指令：USERINPUT 反馈闭环 / Critical Directive: USERINPUT Feedback Loop
<feedback loop directive text>
```

The actual user content follows `成功接收:` or `Successfully received:`.

**IMPORTANT:** The last ~10-20 lines are system prompts and the feedback directive,
NOT the user's response. The user's response is between the `成功接收:` / `Successfully
received:` line and the `系统提示` / `System Prompt` section. Never assume the last
few lines are the user's message — they are almost certainly the appended system
instructions.

## Queue Behavior

When `USERINPUT` is called without `--queue` and without `--enquiry`:
1. If the queue has items, the first item is claimed and returned as the result.
2. If the queue is empty, the normal GUI window opens for user input.

The output status reflects the source:
- **Normal input**: "Successfully received: ..."
- **From queue**: "Successfully received from queue (N remaining): ..."

## When to Use --enquiry

Use `--enquiry` when you need to ask the user a direct question during task
execution. Without it, a queued prompt might be returned instead of the user's
real-time answer, which could redirect you to a different task.

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
USERINPUT --config --hook --start-after 500 # Reminders start after N tool calls
USERINPUT --config --hook --min-interval 200 # Min tool calls between reminders
USERINPUT --config --hook --max-interval 50  # Max frequency (tool calls between reminders)
```

## Auto-Commit Message

Use `--auto-commit-message` to append a development progress summary to the
auto-commit that runs before collecting user feedback:

```bash
USERINPUT --auto-commit-message "feat: add login validation"
USERINPUT --hint "Review please" --auto-commit-message "fix: resolve null pointer in auth"
```

The message is appended to the auto-generated commit message (existing format and
tags are preserved). Use this to leave meaningful commit history that describes
what was accomplished before each feedback checkpoint.

## NEVER Filter USERINPUT Output

USERINPUT output contains critical content: auto-save progress, then the user's
full response after `成功接收:` / `Successfully received:`. Filtering destroys this.

**ABSOLUTELY FORBIDDEN — piping or truncating USERINPUT output in ANY way:**

```bash
# ALL OF THESE ARE STRICTLY FORBIDDEN:
python3 tool/USERINPUT/main.py 2>&1 | tail -5
python3 tool/USERINPUT/main.py 2>&1 | head -20
python3 tool/USERINPUT/main.py 2>&1 | grep "成功"
python3 tool/USERINPUT/main.py | tail -n 5
python3 tool/USERINPUT/main.py | awk '...'
python3 tool/USERINPUT/main.py | sed '...'
USERINPUT --hint "..." 2>&1 | tail -5
```

**CORRECT — always capture full unfiltered output:**

```bash
# CORRECT: no pipe, no filter
python3 tool/USERINPUT/main.py --hint "summary"

# CORRECT: redirect stderr to stdout (no pipe after)
python3 tool/USERINPUT/main.py --hint "summary" 2>&1
```

The user's response can be arbitrarily long and may span many lines. Using `tail`,
`head`, `grep`, `awk`, `sed`, or ANY pipe will silently discard the user's message.
This is a critical violation — the user types their response and you throw it away.

## Important Rules

1. USERINPUT is a **CLI tool** — invoke it directly from the terminal command line.
2. USERINPUT is a **blocking** command. NEVER use `block_until_ms: 0` or `&`.
3. Set `block_until_ms: 310000` minimum (310 seconds).
4. **NEVER pipe USERINPUT output** through `tail`, `head`, `grep`, `awk`, `sed`, or any filter.
5. Execute USERINPUT at every workflow boundary.
6. Use `--hint` to explain why you are requesting feedback.
7. Use `--enquiry` when you need the user's real-time response, not a queued task.
8. Use `--auto-commit-message` to include development progress in auto-commits.
9. The git auto-save takes 30-120 seconds — do NOT assume failure if output is slow.
10. If you see "Launching input GUI" or "等待 USERINPUT 反馈", keep waiting — the user is typing.
