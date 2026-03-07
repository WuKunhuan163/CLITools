---
name: python-best-practices
description: Python development best practices and idioms. Use when working with python best practices concepts or setting up related projects.
---

# Python Best Practices

## Core Principles

- **Readability**: Follow PEP 8; use `black` formatter and `ruff` linter
- **Type Hints**: Annotate function signatures for clarity and IDE support
- **Context Managers**: Use `with` for resource management
- **Comprehensions Over Loops**: When the transformation is simple and readable

## Key Patterns

### Dataclasses
```python
from dataclasses import dataclass, field

@dataclass
class User:
    name: str
    email: str
    tags: list[str] = field(default_factory=list)
```

### Path Handling
```python
from pathlib import Path
config_path = Path.home() / ".config" / "myapp" / "settings.json"
config_path.parent.mkdir(parents=True, exist_ok=True)
```

### Exception Chaining
```python
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    raise ValidationError(f"Invalid JSON input") from e
```

### Generators for Large Data
```python
def read_large_file(path):
    with open(path) as f:
        for line in f:
            yield line.strip()
```

## Project Structure
```
myproject/
  src/myproject/
    __init__.py
    core.py
  tests/
    test_core.py
  pyproject.toml
```

## Anti-Patterns
- Mutable default arguments (`def f(items=[])`; use `None`)
- Bare `except:` (catch specific exceptions)
- Using `os.path` instead of `pathlib`
- Not using virtual environments
