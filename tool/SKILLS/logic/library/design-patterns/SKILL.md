---
name: design-patterns
description: Essential software design patterns. Use when working with design patterns concepts or setting up related projects.
---

# Design Patterns

## Creational Patterns

### Factory Method
```python
class NotificationFactory:
    @staticmethod
    def create(channel: str) -> Notification:
        if channel == "email": return EmailNotification()
        if channel == "sms": return SMSNotification()
        raise ValueError(f"Unknown channel: {channel}")
```

### Builder
```python
query = QueryBuilder().select("name", "email").from_table("users").where("active = true").limit(10).build()
```

### Singleton (use sparingly)
```python
class Config:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

## Structural Patterns

### Adapter
Wrap an incompatible interface to make it compatible with expected interface.

### Decorator
Add behavior to objects dynamically without modifying their class.

## Behavioral Patterns

### Strategy
Swap algorithms at runtime (sorting strategies, discount calculations).

### Observer
Notify multiple objects when state changes (event systems, pub/sub).

### Command
Encapsulate actions as objects (undo/redo, task queues).

## When to Use
- **Factory**: Multiple related types with shared interface
- **Strategy**: Interchangeable algorithms
- **Observer**: Decoupled event handling
- **Decorator**: Adding features without subclassing
