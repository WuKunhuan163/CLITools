---
name: error-handling
description: Error handling patterns across languages. Use when working with error handling concepts or setting up related projects.
---

# Error Handling Patterns

## Core Principles

- **Fail Fast**: Detect errors early; don't let invalid state propagate
- **Use Type System**: Express errors in the type signature (Result types, checked exceptions)
- **Specific Exceptions**: Catch specific errors, not bare `except` / `catch`
- **User-Facing vs Internal**: Different handling for user errors vs system errors

## Patterns by Language

### Python
```python
# Custom exception hierarchy
class AppError(Exception): pass
class NotFoundError(AppError): pass
class ValidationError(AppError): pass

# Context manager for cleanup
with open("file.txt") as f:
    data = f.read()  # auto-closes on exception

# Specific catches
try:
    user = find_user(user_id)
except NotFoundError:
    return {"error": "User not found"}, 404
except ValidationError as e:
    return {"error": str(e)}, 422
```

### Go
```go
// Explicit error return
func findUser(id string) (*User, error) {
    user, err := db.Get(id)
    if err != nil {
        return nil, fmt.Errorf("findUser(%s): %w", id, err)
    }
    return user, nil
}
```

### TypeScript
```ts
// Result type pattern
type Result<T, E = Error> = { ok: true; value: T } | { ok: false; error: E };

function parseJSON(input: string): Result<unknown> {
  try {
    return { ok: true, value: JSON.parse(input) };
  } catch (e) {
    return { ok: false, error: e as Error };
  }
}
```

## Anti-Patterns
- Swallowing exceptions silently (`except: pass`)
- Using exceptions for control flow
- Returning null instead of throwing/returning error
