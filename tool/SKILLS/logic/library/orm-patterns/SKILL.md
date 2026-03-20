---
name: orm-patterns
description: ORM usage patterns and query optimization. Use when working with orm patterns concepts or setting up related projects.
---

# ORM Patterns

## Core Principles

- **Eager Loading**: Specify relationships upfront to avoid N+1 queries
- **Query Scoping**: Use named scopes/managers for common filters
- **Raw SQL When Needed**: ORMs aren't silver bullets; use raw SQL for complex queries
- **Connection Pooling**: Configure pool size based on concurrency needs

## Key Patterns

### Eager Loading (SQLAlchemy)
```python
# N+1 problem
users = session.query(User).all()
for u in users: print(u.posts)  # N extra queries

# Eager loading solution
users = session.query(User).options(joinedload(User.posts)).all()
```

### Repository Pattern
```python
class UserRepository:
    def __init__(self, session):
        self.session = session

    def find_active(self) -> list[User]:
        return self.session.query(User).filter(User.active == True).all()

    def find_by_email(self, email: str) -> User | None:
        return self.session.query(User).filter(User.email == email).first()
```

## Anti-Patterns
- Loading entire tables into memory
- Using ORM for bulk operations (use raw SQL or batch APIs)
- Putting query logic in views/controllers instead of repositories
