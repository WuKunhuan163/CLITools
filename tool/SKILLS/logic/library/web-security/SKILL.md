---
name: web-security
description: Web application security (OWASP Top 10). Use when working with web security concepts or setting up related projects.
---

# Web Security (OWASP)

## OWASP Top 10 (Key Items)

### 1. Injection (SQL, NoSQL, Command)
```python
# Bad
query = f"SELECT * FROM users WHERE email = '{email}'"
# Good (parameterized)
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

### 2. Broken Authentication
- Enforce strong passwords
- Implement MFA
- Rate-limit login attempts
- Use secure session management

### 3. Cross-Site Scripting (XSS)
```html
<!-- Bad: unescaped user input -->
<div>{user_input}</div>
<!-- Good: frameworks auto-escape (React, Vue, Angular) -->
<!-- If raw HTML needed, sanitize with DOMPurify -->
```

### 4. Insecure Direct Object References (IDOR)
```python
# Bad: user can access any order by changing ID
@app.get("/orders/{id}")
def get_order(id):
    return db.orders.find(id)

# Good: verify ownership
@app.get("/orders/{id}")
def get_order(id, user=Depends(get_current_user)):
    order = db.orders.find(id)
    if order.user_id != user.id:
        raise HTTPException(403)
```

### 5. Security Misconfiguration
- Remove default credentials
- Disable directory listing
- Set security headers (CSP, HSTS, X-Frame-Options)
- Keep dependencies updated

## Security Headers
```
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```
