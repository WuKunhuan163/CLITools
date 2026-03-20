---
name: secrets-management
description: Secrets management and secure configuration. Use when working with secrets management concepts or setting up related projects.
---

# Secrets Management

## Core Principles

- **Never in Code**: Secrets must not appear in source code or version control
- **Encrypt at Rest**: Store secrets encrypted, decrypt at runtime
- **Least Privilege**: Each service gets only the secrets it needs
- **Rotation**: Secrets should be rotatable without downtime

## Approaches

### Environment Variables (Simple)
```python
import os
db_password = os.environ["DATABASE_PASSWORD"]
```

### .env Files (Development)
```
# .env (NEVER commit this)
DATABASE_URL=postgres://user:pass@localhost/db
API_KEY=sk-12345
```
```python
from dotenv import load_dotenv
load_dotenv()
```

### Secret Managers (Production)
- **AWS Secrets Manager**: Automatic rotation, IAM-based access
- **HashiCorp Vault**: Self-hosted, dynamic secrets, leasing
- **GCP Secret Manager**: Version-controlled secrets

### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
stringData:
  password: super-secret
```

## Checklist
- `.env` and credential files in `.gitignore`
- CI/CD uses secret injection (GitHub Secrets, Vault)
- Secrets rotated on schedule (90 days minimum)
- Audit log for secret access
- No secrets in Docker images or build args
