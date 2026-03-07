---
name: semantic-versioning
description: Semantic versioning and release management. Use when working with semantic versioning concepts or setting up related projects.
---

# Semantic Versioning

## Version Format: MAJOR.MINOR.PATCH

- **MAJOR** (1.0.0 -> 2.0.0): Breaking changes; incompatible API changes
- **MINOR** (1.0.0 -> 1.1.0): New features; backward compatible
- **PATCH** (1.0.0 -> 1.0.1): Bug fixes; backward compatible

## Pre-Release Labels
```
1.0.0-alpha.1    # Early development
1.0.0-beta.1     # Feature complete, testing
1.0.0-rc.1       # Release candidate
```

## Decision Guide

### Bump MAJOR when:
- Removing a public API
- Changing function signatures
- Changing behavior in incompatible ways

### Bump MINOR when:
- Adding new endpoints/functions
- Adding optional parameters
- Deprecating (but not removing) features

### Bump PATCH when:
- Fixing bugs
- Performance improvements
- Internal refactoring

## Changelog Pattern
```markdown
## [1.2.0] - 2026-03-01
### Added
- User profile photo upload endpoint
### Fixed
- Race condition in concurrent order updates
### Deprecated
- `/api/v1/legacy-auth` endpoint (use `/api/v2/auth`)
```

## Automation
- Use `standard-version` or `semantic-release` to automate
- Conventional commits drive automatic version bumps
