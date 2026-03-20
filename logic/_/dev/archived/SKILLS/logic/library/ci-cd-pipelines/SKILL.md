---
name: ci-cd-pipelines
description: CI/CD pipeline design and best practices. Use when working with ci cd pipelines concepts or setting up related projects.
---

# CI/CD Pipelines

## Core Principles

- **Fast Feedback**: Run fastest checks first (lint, type check, then unit tests)
- **Reproducible Builds**: Pin dependency versions; use lock files
- **Trunk-Based Development**: Merge to main frequently; feature flags over long branches
- **Progressive Delivery**: Canary deployments, blue-green, feature flags

## Pipeline Stages

```
1. Lint & Format Check  (seconds)
2. Type Check           (seconds)
3. Unit Tests           (minutes)
4. Build                (minutes)
5. Integration Tests    (minutes)
6. Security Scan        (minutes)
7. Deploy to Staging    (minutes)
8. E2E Tests            (minutes)
9. Deploy to Production (manual gate or auto)
```

## GitHub Actions Example
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
```

## Anti-Patterns
- Running all tests sequentially (parallelize where possible)
- No caching of dependencies between runs
- Manual deployment processes
- Not failing fast on lint/type errors
