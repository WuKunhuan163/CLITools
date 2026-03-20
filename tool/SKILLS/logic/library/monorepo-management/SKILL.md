---
name: monorepo-management
description: Monorepo management patterns and tools. Use when working with monorepo management concepts or setting up related projects.
---

# Monorepo Management

## Core Principles

- **Single Source of Truth**: All code in one repository
- **Atomic Changes**: Cross-package changes in single commit
- **Selective CI**: Only build/test what changed
- **Workspace Management**: Share dependencies efficiently

## Tools

### JavaScript/TypeScript
- **Turborepo**: Fast builds with caching and parallelism
- **Nx**: Full-featured monorepo toolkit with dependency graph
- **pnpm workspaces**: Efficient package management

### Multi-Language
- **Bazel**: Google's build system, language-agnostic
- **Pants**: Python-first but supports multiple languages

## Package Structure
```
monorepo/
  packages/
    shared-ui/         # Shared component library
    api-client/        # Auto-generated API client
  apps/
    web/               # Next.js web app
    mobile/            # React Native app
    api/               # Backend service
  package.json         # Root workspace config
  turbo.json           # Build pipeline config
```

## Turborepo Configuration
```json
{
  "pipeline": {
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**"] },
    "test": { "dependsOn": ["build"] },
    "lint": {}
  }
}
```

## Anti-Patterns
- No clear ownership of packages
- Circular dependencies between packages
- Building everything on every change (no affected detection)
- Shared package with breaking changes affecting all consumers
