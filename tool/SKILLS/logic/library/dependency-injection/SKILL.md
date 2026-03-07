---
name: dependency-injection
description: Dependency injection patterns across frameworks. Use when working with dependency injection concepts or setting up related projects.
---

# Dependency Injection

## Core Principles

- **Inversion of Control**: Don't create dependencies; receive them
- **Constructor Injection**: Preferred method; makes dependencies explicit
- **Interface Segregation**: Depend on abstractions, not implementations
- **Composition Root**: Wire dependencies at application startup

## Patterns

### Manual DI (Python)
```python
class UserService:
    def __init__(self, repo: UserRepository, mailer: EmailService):
        self.repo = repo
        self.mailer = mailer

# Composition root
repo = PostgresUserRepository(db)
mailer = SMTPEmailService(config)
service = UserService(repo, mailer)
```

### FastAPI Depends
```python
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

### Spring (Java)
```java
@Service
public class OrderService {
    private final OrderRepository repo;
    public OrderService(OrderRepository repo) { this.repo = repo; }
}
```

## Benefits
- Testability: swap real implementations with fakes/mocks
- Flexibility: change implementations without modifying consumers
- Explicit dependencies: constructor shows what a class needs

## Anti-Patterns
- Service locator pattern (hides dependencies)
- Injecting the DI container itself
- Circular dependencies
