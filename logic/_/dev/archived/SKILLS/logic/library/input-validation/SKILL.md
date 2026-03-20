---
name: input-validation
description: Input validation and sanitization patterns. Use when working with input validation concepts or setting up related projects.
---

# Input Validation & Sanitization

## Core Principles

- **Validate Early**: Check input at the boundary (API endpoint, form handler)
- **Whitelist Over Blacklist**: Define what's allowed, not what's forbidden
- **Type Coercion**: Convert inputs to expected types immediately
- **Separate Validation from Business Logic**: Use schema validators

## Patterns

### Pydantic (Python)
```python
from pydantic import BaseModel, EmailStr, constr

class UserCreate(BaseModel):
    name: constr(min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(ge=0, le=150)
```

### Zod (TypeScript)
```ts
import { z } from 'zod';

const UserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email(),
  age: z.number().int().min(0).max(150),
});

type User = z.infer<typeof UserSchema>;
const user = UserSchema.parse(input); // throws on invalid
```

### SQL Parameterization
```python
# Always use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

## Sanitization
- **HTML**: DOMPurify for user-generated HTML content
- **SQL**: Parameterized queries (never string interpolation)
- **File Uploads**: Validate MIME type, file size, file name characters
- **URLs**: Validate scheme (http/https only), prevent SSRF

## Anti-Patterns
- Validating only on the client side
- Using regex for email validation (use a library)
- Trusting HTTP headers for security decisions
