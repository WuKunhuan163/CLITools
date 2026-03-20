---
name: authentication-patterns
description: Authentication and authorization patterns (JWT, OAuth, sessions). Use when working with authentication patterns concepts or setting up related projects.
---

# Authentication Patterns

## Core Principles

- **JWT for Stateless Auth**: Token contains claims; verify without DB lookup
- **Sessions for Server-Side Auth**: Store session in Redis/DB; cookie holds session ID
- **OAuth 2.0 / OIDC**: Delegate authentication to identity providers
- **RBAC/ABAC**: Role-based or attribute-based access control for authorization

## JWT Pattern
```python
import jwt

def create_token(user_id: int, secret: str) -> str:
    return jwt.encode(
        {"sub": user_id, "exp": datetime.utcnow() + timedelta(hours=1)},
        secret, algorithm="HS256"
    )

def verify_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])
```

## OAuth 2.0 Authorization Code Flow
1. Redirect user to provider's `/authorize` endpoint
2. User authenticates and consents
3. Provider redirects back with `code`
4. Backend exchanges `code` for `access_token` via `/token`
5. Use `access_token` to fetch user info

## Security Checklist
- Store tokens in `httpOnly`, `secure`, `sameSite` cookies (not localStorage)
- Implement token refresh rotation
- Always validate JWT `exp`, `iss`, `aud` claims
- Rate-limit login endpoints
- Use bcrypt/argon2 for password hashing (never MD5/SHA1)
