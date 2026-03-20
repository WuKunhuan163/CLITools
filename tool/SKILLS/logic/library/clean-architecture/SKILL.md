---
name: clean-architecture
description: Clean Architecture and hexagonal design patterns. Use when working with clean architecture concepts or setting up related projects.
---

# Clean Architecture

## Core Principle: Dependency Rule

Dependencies point inward. Inner layers know nothing about outer layers.

```
[Frameworks & Drivers] -> [Interface Adapters] -> [Use Cases] -> [Entities]
```

## Layer Responsibilities

### Entities (innermost)
Pure business objects with business rules. No framework dependencies.

### Use Cases
Application-specific business rules. Orchestrate entities.

### Interface Adapters
Convert data between use cases and external formats (controllers, presenters, repositories).

### Frameworks & Drivers (outermost)
Databases, web frameworks, UI. All implementation details.

## Implementation Pattern
```python
# Entity
class Order:
    def calculate_total(self): ...

# Use Case (port)
class CreateOrderUseCase:
    def __init__(self, order_repo: OrderRepository): ...
    def execute(self, dto: CreateOrderDTO) -> Order: ...

# Repository Interface (port)
class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order): ...

# Adapter (implementation)
class PostgresOrderRepository(OrderRepository):
    def save(self, order: Order): ...
```

## Benefits
- Business logic testable without database/framework
- Framework can be swapped without touching business logic
- Use cases are explicit and discoverable
