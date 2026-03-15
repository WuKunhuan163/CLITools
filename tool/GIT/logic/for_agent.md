# GIT Logic — Technical Reference

## engine.py — GitEngine

```python
GitEngine(project_root=None)
```

- `run_git(args, cwd=None)`: Execute git subprocess with error handling
- `get_current_branch()`: Returns current branch name
- GitHub API interactions with rate limit awareness
- Uses `requests` for HTTP calls, `subprocess` for git commands

## Gotchas

1. **project_root optional**: If None, uses current working directory for git commands.
2. **GitHub rate limits**: Engine handles 403/rate-limit responses from GitHub API.
