---
name: unit-testing
description: Unit testing principles and best practices. Use when working with unit testing concepts or setting up related projects.
---

# Unit Testing Best Practices

## Core Principles

- **AAA Pattern**: Arrange, Act, Assert -- structure every test this way
- **Isolation**: Test one behavior per test; mock external dependencies
- **Fast**: Unit tests should run in milliseconds
- **Descriptive Names**: Test name should describe the behavior being tested

## Key Patterns

### AAA Pattern
```python
def test_discount_applied_for_premium_users():
    # Arrange
    user = User(tier="premium")
    cart = Cart(items=[Item(price=100)])
    # Act
    total = calculate_total(cart, user)
    # Assert
    assert total == 90  # 10% discount
```

### Parameterized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("", ""),
    ("Hello World", "HELLO WORLD"),
])
def test_uppercase(input, expected):
    assert to_upper(input) == expected
```

### Test Doubles
- **Stub**: Returns predetermined data
- **Mock**: Verifies interactions (was method called?)
- **Fake**: Working implementation (in-memory database)
- **Spy**: Records calls for later verification

## Anti-Patterns
- Testing implementation details (private methods, internal state)
- Tests that depend on execution order
- Excessive mocking (test becomes a mirror of implementation)
- No assertions (test always passes)
