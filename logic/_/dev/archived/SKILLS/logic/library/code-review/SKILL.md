---
name: code-review
description: Code review best practices and checklist. Use when working with code review concepts or setting up related projects.
---

# Code Review Best Practices

## Reviewer Guidelines

### What to Look For
1. **Correctness**: Does the code do what it claims?
2. **Design**: Is it well-structured? Does it follow project patterns?
3. **Readability**: Can someone new understand it?
4. **Performance**: Any O(n^2) loops, N+1 queries, memory leaks?
5. **Security**: Input validation, SQL injection, XSS, auth checks?
6. **Tests**: Are new behaviors tested? Are edge cases covered?

### How to Give Feedback
- **Be specific**: Point to exact lines and suggest alternatives
- **Explain why**: Not just "change this" but "this could cause X because Y"
- **Distinguish severity**: Use prefixes like `nit:`, `suggestion:`, `blocker:`
- **Praise good code**: Acknowledge clean solutions and clever approaches

## Author Guidelines

- **Small PRs**: Aim for <400 lines changed; split large features
- **Self-Review First**: Review your own diff before requesting reviews
- **Good Description**: Explain what, why, and how to test
- **Respond Promptly**: Don't let reviews stall; address feedback daily

## PR Template
```markdown
## What
Brief description of changes

## Why
Problem being solved or feature being added

## How to Test
Steps to verify the change works

## Screenshots (if UI)
```

## Anti-Patterns
- Rubber-stamping (approving without reading)
- Nitpicking style issues (use linters instead)
- Blocking on personal preference (not wrong, just different)
