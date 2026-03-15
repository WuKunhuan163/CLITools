---
name: technical-debt
description: Technical debt identification and management. Use when working with technical debt concepts or setting up related projects.
---

# Technical Debt Management

## Types of Technical Debt

### Deliberate (Strategic)
- Conscious trade-offs for speed (documented, planned payoff)
- Example: "Ship MVP without caching; add before launch"

### Accidental (Discovery)
- Learned a better approach after building
- Example: "Realize the schema should be normalized differently"

### Bit Rot (Entropy)
- Code degrades as requirements change around it
- Example: "Auth module wasn't designed for multi-tenant"

## Identification

### Code Metrics
- **Cyclomatic Complexity**: Functions with complexity > 10
- **Code Duplication**: Clone detection tools (jscpd, CPD)
- **Dependency Age**: Outdated packages with known vulnerabilities
- **Test Coverage Gaps**: Critical paths without tests

### Code Smells
- Long methods (>30 lines)
- Large classes (>300 lines)
- Deep nesting (>3 levels)
- Commented-out code
- TODO/FIXME/HACK comments

## Management Strategies

### Boy Scout Rule
Leave code better than you found it. Small improvements with each change.

### Debt Budget
Allocate 15-20% of sprint capacity to tech debt reduction.

### Tech Debt Register
Track items with: description, impact, effort, priority.

### Strangler Fig Pattern
Incrementally replace legacy system by routing new functionality through new code.

## Anti-Patterns
- Rewriting everything at once ("big bang" migration)
- Ignoring debt until it blocks feature development
- Not tracking debt formally (it becomes invisible)
