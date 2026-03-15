---
name: git-workflow
description: Git branching strategies and workflow patterns. Use when working with git workflow concepts or setting up related projects.
---

# Git Workflow & Branching

## Strategies

### Trunk-Based Development (Recommended)
- All developers commit to `main` (or short-lived feature branches)
- Feature flags control incomplete features
- CI/CD deploys main continuously

### GitHub Flow
1. Create branch from `main`
2. Make commits
3. Open Pull Request
4. Review and discuss
5. Merge to `main`
6. Deploy

### GitFlow (Legacy/Complex releases)
- `main`: production code
- `develop`: integration branch
- `feature/*`: new features
- `release/*`: release preparation
- `hotfix/*`: production fixes

## Commit Best Practices

### Conventional Commits
```
feat: add user registration endpoint
fix: resolve race condition in payment processing
refactor: extract validation logic into middleware
docs: update API documentation for v2 endpoints
test: add integration tests for order service
```

## Key Commands
```bash
git rebase -i HEAD~3           # Squash/reorder last 3 commits
git stash push -m "wip"        # Stash with message
git cherry-pick <sha>          # Apply specific commit
git bisect start/bad/good      # Binary search for bug introduction
git reflog                     # Recovery: find lost commits
```

## Anti-Patterns
- Long-lived feature branches (merge conflicts accumulate)
- Force-pushing to shared branches
- Committing generated files or secrets
