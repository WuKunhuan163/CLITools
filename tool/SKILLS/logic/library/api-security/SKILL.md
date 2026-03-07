---
name: api-security
description: API security patterns and best practices. Use when working with api security concepts or setting up related projects.
---

# API Security

## Authentication

- **API Keys**: Simple but limited (identify caller, not authorize)
- **OAuth 2.0 Bearer Tokens**: Standard for user-delegated access
- **mTLS**: Mutual TLS for service-to-service authentication

## Authorization

- Check permissions on every request (not just authentication)
- Implement RBAC or ABAC at the middleware level
- Never trust client-side authorization checks alone

## Common Protections

### Rate Limiting
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1672531200
```

### Request Validation
- Validate Content-Type header
- Enforce request size limits
- Validate all path/query parameters

### CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,
    allow_origins=["https://myapp.com"],  # not "*" in production
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"],
)
```

## Security Headers for APIs
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Cache-Control: no-store
```

## Anti-Patterns
- CORS `allow_origins=["*"]` with credentials
- API keys in URL query parameters (use headers)
- No rate limiting on authentication endpoints
- Verbose error messages exposing internals
