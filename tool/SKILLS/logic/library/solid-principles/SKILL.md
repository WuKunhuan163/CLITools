---
name: solid-principles
description: SOLID object-oriented design principles. Use when working with solid principles concepts or setting up related projects.
---

# SOLID Principles

## The Five Principles

### S - Single Responsibility
A class should have only one reason to change.
```python
# Bad: class handles both user logic and email sending
# Good: separate UserService and EmailService
```

### O - Open/Closed
Open for extension, closed for modification.
```python
# Use strategy pattern or polymorphism instead of if/else chains
class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, amount: float) -> float: ...

class PercentageDiscount(DiscountStrategy):
    def __init__(self, percent): self.percent = percent
    def calculate(self, amount): return amount * (1 - self.percent)
```

### L - Liskov Substitution
Subtypes must be substitutable for their base types without breaking behavior.

### I - Interface Segregation
Clients should not depend on interfaces they don't use. Prefer many small interfaces over one large one.

### D - Dependency Inversion
High-level modules should depend on abstractions, not concrete implementations.
```python
# Bad: OrderService directly creates MySQLDatabase
# Good: OrderService accepts a Database interface
class OrderService:
    def __init__(self, db: DatabaseInterface):
        self.db = db
```

## When to Apply
- Refactoring code that's hard to change
- Designing new systems that need flexibility
- Code review: check if changes cascade unnecessarily
