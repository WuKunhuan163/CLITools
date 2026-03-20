---
name: documentation-practices
description: Code documentation and API documentation best practices. Use when working with documentation practices concepts or setting up related projects.
---

# Documentation Practices

## Core Principles

- **Code Is the Primary Documentation**: Write self-documenting code first
- **Document Why, Not What**: Comments explain intent, not mechanics
- **Keep Docs Near Code**: Docstrings, README in same directory
- **Automate Where Possible**: Generate API docs from code annotations

## What to Document

### Always Document
- Public APIs (function signatures, parameters, return values)
- Non-obvious design decisions (why, not what)
- Setup and deployment procedures
- Architecture decisions (ADRs)

### Never Document
- Obvious code (`i++ // increment i`)
- Implementation details that change frequently
- Things enforceable by linters/types

## Patterns

### Python Docstrings
```python
def calculate_shipping(weight: float, destination: str) -> Decimal:
    """Calculate shipping cost based on weight and destination zone.

    Args:
        weight: Package weight in kilograms.
        destination: ISO 3166-1 alpha-2 country code.

    Returns:
        Shipping cost in USD.

    Raises:
        ValueError: If weight is negative or destination is unknown.
    """
```

### Architecture Decision Record (ADR)
```markdown
# ADR-001: Use PostgreSQL for primary database
## Status: Accepted
## Context: Need ACID transactions, JSON support, and mature ecosystem
## Decision: PostgreSQL 16 with JSONB for flexible schemas
## Consequences: Team needs PostgreSQL expertise; migration from SQLite needed
```
