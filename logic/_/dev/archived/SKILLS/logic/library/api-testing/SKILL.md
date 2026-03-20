---
name: api-testing
description: API testing patterns and tools. Use when working with api testing concepts or setting up related projects.
---

# API Testing

## Core Principles

- **Contract Testing**: Verify API matches its specification
- **Status Codes**: Test all expected status codes (200, 400, 401, 404, 500)
- **Edge Cases**: Empty bodies, missing fields, invalid types, boundary values
- **Authentication**: Test with valid, invalid, and missing credentials

## Key Patterns

### Python (pytest + requests)
```python
def test_create_user():
    response = requests.post("/api/users", json={"name": "Alice", "email": "a@b.com"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert "id" in data

def test_create_user_missing_email():
    response = requests.post("/api/users", json={"name": "Alice"})
    assert response.status_code == 422
```

### Schema Validation
```python
from jsonschema import validate
schema = {
    "type": "object",
    "required": ["id", "name", "email"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"}
    }
}
validate(response.json(), schema)
```

## Testing Checklist
- Happy path for all endpoints
- Validation errors (400/422)
- Authentication/authorization (401/403)
- Not found (404)
- Duplicate resources (409)
- Rate limiting (429)
