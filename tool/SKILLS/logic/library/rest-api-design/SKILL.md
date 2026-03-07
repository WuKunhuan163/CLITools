---
name: rest-api-design
description: RESTful API design principles and patterns. Use when working with rest api design concepts or setting up related projects.
---

# REST API Design

## Core Principles

- **Resource-Oriented**: URLs represent resources (nouns), not actions (verbs)
- **HTTP Methods**: GET (read), POST (create), PUT (replace), PATCH (partial update), DELETE (remove)
- **Status Codes**: Use correct codes (200, 201, 204, 400, 401, 403, 404, 409, 422, 500)
- **Versioning**: Use URL path (`/v1/`) or header-based versioning

## URL Design

```
GET    /api/v1/users          # List users
POST   /api/v1/users          # Create user
GET    /api/v1/users/:id      # Get user
PATCH  /api/v1/users/:id      # Update user
DELETE /api/v1/users/:id      # Delete user
GET    /api/v1/users/:id/posts # User's posts (relationship)
```

## Response Format
```json
{
  "data": { "id": 1, "name": "Alice" },
  "meta": { "request_id": "abc-123" }
}
```

## Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": [{ "field": "email", "constraint": "required" }]
  }
}
```

## Pagination
- Cursor-based: `?cursor=abc&limit=20` (preferred for real-time data)
- Offset-based: `?page=2&per_page=20` (simpler, worse for large datasets)
