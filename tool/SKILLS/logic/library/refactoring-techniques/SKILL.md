---
name: refactoring-techniques
description: Code refactoring techniques and strategies. Use when working with refactoring techniques concepts or setting up related projects.
---

# Refactoring Techniques

## Core Principles

- **Refactor Under Tests**: Never refactor without passing tests as a safety net
- **Small Steps**: One transformation at a time; run tests between each
- **Boy Scout Rule**: Leave code better than you found it
- **Code Smells Guide Refactoring**: Each smell has specific refactoring techniques

## Common Refactorings

### Extract Function
```python
# Before
def process_order(order):
    # validate
    if not order.items: raise ValueError("Empty order")
    if order.total < 0: raise ValueError("Negative total")
    # process
    ...

# After
def process_order(order):
    validate_order(order)
    ...

def validate_order(order):
    if not order.items: raise ValueError("Empty order")
    if order.total < 0: raise ValueError("Negative total")
```

### Replace Conditional with Polymorphism
```python
# Before
def calculate_area(shape):
    if shape.type == "circle": return math.pi * shape.radius ** 2
    if shape.type == "rect": return shape.width * shape.height

# After
class Circle:
    def area(self): return math.pi * self.radius ** 2
class Rectangle:
    def area(self): return self.width * self.height
```

### Introduce Parameter Object
```python
# Before
def search(query, page, per_page, sort_by, sort_order): ...

# After
@dataclass
class SearchParams:
    query: str
    page: int = 1
    per_page: int = 20
    sort_by: str = "relevance"
    sort_order: str = "desc"

def search(params: SearchParams): ...
```

## Code Smells -> Refactoring
- **Long Method** -> Extract Function
- **Large Class** -> Extract Class
- **Feature Envy** -> Move Method
- **Primitive Obsession** -> Introduce Value Object
- **Duplicate Code** -> Extract & Share
