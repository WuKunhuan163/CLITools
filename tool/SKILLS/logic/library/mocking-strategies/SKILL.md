---
name: mocking-strategies
description: Test mocking and stubbing strategies. Use when working with mocking strategies concepts or setting up related projects.
---

# Mocking Strategies

## Core Principles

- **Mock at Boundaries**: Mock external services, not internal implementation
- **Prefer Fakes Over Mocks**: In-memory implementations are more reliable than mock assertions
- **Verify Behavior, Not Implementation**: Test what happened, not how
- **Minimal Mocking**: If you're mocking too much, the code might need refactoring

## Python Patterns

### unittest.mock
```python
from unittest.mock import patch, MagicMock

@patch('myapp.services.email_client')
def test_sends_welcome_email(mock_email):
    register_user("alice@example.com")
    mock_email.send.assert_called_once_with(
        to="alice@example.com",
        subject="Welcome!"
    )
```

### Fake Implementation
```python
class FakeUserRepository:
    def __init__(self):
        self.users = {}
    def save(self, user):
        self.users[user.id] = user
    def find(self, user_id):
        return self.users.get(user_id)
```

## JavaScript Patterns

### Jest Mocks
```js
jest.mock('./api', () => ({
  fetchUser: jest.fn().mockResolvedValue({ id: 1, name: 'Alice' }),
}));
```

## Anti-Patterns
- Mocking the system under test
- Testing that a mock was called with exact implementation details
- Not resetting mocks between tests
