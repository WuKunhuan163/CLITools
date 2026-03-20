---
name: secure-coding
description: Secure coding practices across languages. Use when working with secure coding concepts or setting up related projects.
---

# Secure Coding Practices

## Core Principles

- **Least Privilege**: Code and processes run with minimum necessary permissions
- **Defense in Depth**: Multiple security layers, not just one
- **Fail Securely**: Errors should not reveal sensitive information or grant access
- **Input is Hostile**: All external input is untrusted until validated

## Language-Specific Practices

### Python
```python
import secrets  # not random, for security
token = secrets.token_urlsafe(32)

import subprocess
subprocess.run(["ls", "-la", user_dir], check=True)  # not shell=True
```

### JavaScript/TypeScript
```js
// Use textContent, not innerHTML for user data
element.textContent = userInput;

// Avoid eval() and new Function() with user input
// Use JSON.parse() for JSON, not eval()
```

### SQL
```python
# Always parameterized
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
# Never: f"SELECT * FROM users WHERE id = {user_id}"
```

## Dependency Security
- `npm audit` / `pip-audit` / `snyk` for vulnerability scanning
- Pin dependency versions in lock files
- Automate security updates (Dependabot, Renovate)
- Review dependency licenses

## Logging Security
- Never log passwords, tokens, or PII
- Use structured logging with redaction
- Log authentication attempts and failures
