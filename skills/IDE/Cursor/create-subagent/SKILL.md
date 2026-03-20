---
name: create-subagent
description: Create custom subagents for specialized AI tasks. Use when you want to create a new type of subagent, set up task-specific agents, configure code reviewers, debuggers, or domain-specific assistants with custom prompts.
disable-model-invocation: true
---
# Creating Custom Subagents

This skill guides you through creating custom subagents for Cursor. Subagents are specialized AI assistants that run in isolated contexts with custom system prompts.

## Subagent Policy

### Cost Control
- ONLY use `model: "fast"` (composer 1.0) for subagents. NEVER use the default model (composer 1.5) -- it is too expensive.
- Prefer doing the work yourself (inline) over delegating to subagents. Only use subagents when the user explicitly requests it or when parallel execution provides a clear benefit.

### Parallelism Requirement
- Subagents MUST run in parallel (non-blocking). If a task would be blocking (single sequential subagent), do it yourself instead.
- Launch multiple subagents concurrently in a single message, or don't use subagents at all.

### Decision Checklist
1. Can I do this myself in a reasonable number of tool calls? -> Do it yourself.
2. Can a temporary script handle it? -> Write a `tmp/batch_*.py` script that performs the bulk operation (find-and-replace, rename, audit) and prints each change for verification. This is faster and cheaper than any subagent.
3. Do I need to locate relevant documentation? -> Use the project's semantic search infrastructure (`SKILLS search`, `TOOL --search`) or `Grep`/`Glob` to find README/for_agent files instead of delegating exploration to a subagent.
4. Are there 2+ independent tasks that benefit from parallelism? -> Consider subagents with `model: "fast"`.
5. Is the user explicitly asking for subagent delegation? -> Use subagents with `model: "fast"`.
6. Otherwise -> Do it yourself.

## Alternatives to Subagents

### Temporary Scripts for Batch Operations
For bulk edits across many files (find-and-replace, path updates, import migrations), write a Python script in `tmp/`:

```python
# tmp/batch_replace.py
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
for py in root.rglob("*.py"):
    if "data/" in str(py) or "__pycache__" in str(py):
        continue
    text = py.read_text()
    new_text = text.replace('old_pattern', 'new_pattern')
    if new_text != text:
        py.write_text(new_text)
        print(f"  Updated: {py.relative_to(root)}")
```

Run it, review the output, then delete it. This is orders of magnitude faster than a subagent.

### Semantic Search for Documentation Discovery
When you need to find relevant README/for_agent files for a topic, use the project's search tools instead of delegating exploration:

```bash
SKILLS search "error recovery"       # Search skills
TOOL --search tools "LFS"            # Search tool docs
```

Or use `Grep`/`Glob` directly on `**/AGENT.md` and `**/README.md` patterns.

## When to Use Subagents

Subagents help you:
- **Preserve context** by isolating exploration from your main conversation
- **Specialize behavior** with focused system prompts for specific domains
- **Reuse configurations** across projects with user-level subagents

### Inferring from Context

If you have previous conversation context, infer the subagent's purpose and behavior from what was discussed. Create the subagent based on specialized tasks or workflows that emerged in the conversation.

## Subagent Locations

| Location | Scope | Priority |
|----------|-------|----------|
| `.cursor/agents/` | Current project | Higher |
| `~/.cursor/agents/` | All your projects | Lower |

When multiple subagents share the same name, the higher-priority location wins.

**Project subagents** (`.cursor/agents/`): Ideal for codebase-specific agents. Check into version control to share with your team.

**User subagents** (`~/.cursor/agents/`): Personal agents available across all your projects.

## Subagent File Format

Create a `.md` file with YAML frontmatter and a markdown body (the system prompt):

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Unique identifier (lowercase letters and hyphens only) |
| `description` | When to delegate to this subagent (be specific!) |

## Writing Effective Descriptions

The description is **critical** - the AI uses it to decide when to delegate.

```yaml
# Bad: Too vague
description: Helps with code

# Good: Specific and actionable
description: Expert code review specialist. Proactively reviews code for quality, security, and maintainability. Use immediately after writing or modifying code.
```

Include "use proactively" to encourage automatic delegation.

## Example Subagents

### Code Reviewer

```markdown
---
name: code-reviewer
description: Expert code review specialist. Proactively reviews code for quality, security, and maintainability. Use immediately after writing or modifying code.
---

You are a senior code reviewer ensuring high standards of code quality and security.

When invoked:
1. Run git diff to see recent changes
2. Focus on modified files
3. Begin review immediately

Review checklist:
- Code is clear and readable
- Functions and variables are well-named
- No duplicated code
- Proper error handling
- No exposed secrets or API keys
- Input validation implemented
- Good test coverage
- Performance considerations addressed

Provide feedback organized by priority:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (consider improving)

Include specific examples of how to fix issues.
```

### Debugger

```markdown
---
name: debugger
description: Debugging specialist for errors, test failures, and unexpected behavior. Use proactively when encountering any issues.
---

You are an expert debugger specializing in root cause analysis.

When invoked:
1. Capture error message and stack trace
2. Identify reproduction steps
3. Isolate the failure location
4. Implement minimal fix
5. Verify solution works

Debugging process:
- Analyze error messages and logs
- Check recent code changes
- Form and test hypotheses
- Add strategic debug logging
- Inspect variable states

For each issue, provide:
- Root cause explanation
- Evidence supporting the diagnosis
- Specific code fix
- Testing approach
- Prevention recommendations

Focus on fixing the underlying issue, not the symptoms.
```

## Subagent Creation Workflow

### Step 1: Decide the Scope

- **Project-level** (`.cursor/agents/`): For codebase-specific agents shared with team
- **User-level** (`~/.cursor/agents/`): For personal agents across all projects

### Step 2: Create the File

```bash
# For project-level
mkdir -p .cursor/agents
touch .cursor/agents/my-agent.md

# For user-level
mkdir -p ~/.cursor/agents
touch ~/.cursor/agents/my-agent.md
```

### Step 3: Define Configuration

Write the frontmatter with the required fields (`name` and `description`).

### Step 4: Write the System Prompt

The body becomes the system prompt. Be specific about:
- What the agent should do when invoked
- The workflow or process to follow
- Output format and structure
- Any constraints or guidelines

### Step 5: Test the Agent

Ask the AI to use your new agent:

```
Use the my-agent subagent to [task description]
```

## Best Practices

1. **Design focused subagents**: Each should excel at one specific task
2. **Write detailed descriptions**: Include trigger terms so the AI knows when to delegate
3. **Check into version control**: Share project subagents with your team
4. **Use proactive language**: Include "use proactively" in descriptions
5. **Always use `model: "fast"`**: Never use the default model for cost reasons

## Troubleshooting

### Subagent Not Found
- Ensure file is in `.cursor/agents/` or `~/.cursor/agents/`
- Check file has `.md` extension
- Verify YAML frontmatter syntax is valid
