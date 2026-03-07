---
name: github-actions
description: GitHub Actions workflow patterns. Use when working with github actions concepts or setting up related projects.
---

# GitHub Actions

## Core Concepts

- **Workflow**: YAML file in `.github/workflows/`, triggered by events
- **Job**: Set of steps running on a runner; jobs run in parallel by default
- **Step**: Individual command or action
- **Matrix Strategy**: Run same job with different configurations

## Key Patterns

### Matrix Testing
```yaml
strategy:
  matrix:
    node-version: [18, 20, 22]
    os: [ubuntu-latest, macos-latest]
runs-on: ${{ matrix.os }}
steps:
  - uses: actions/setup-node@v4
    with: { node-version: ${{ matrix.node-version }} }
```

### Caching Dependencies
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

### Reusable Workflow
```yaml
# .github/workflows/deploy.yml
on:
  workflow_call:
    inputs:
      environment: { required: true, type: string }
```

### Branch Protection
```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
```

## Anti-Patterns
- Hardcoding secrets in workflows (use `${{ secrets.* }}`)
- Not caching dependencies
- Running everything sequentially when jobs are independent
