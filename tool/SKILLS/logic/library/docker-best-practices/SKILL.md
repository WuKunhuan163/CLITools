---
name: docker-best-practices
description: Docker containerization best practices. Use when working with docker best practices concepts or setting up related projects.
---

# Docker Best Practices

## Core Principles

- **Small Images**: Use multi-stage builds; start from slim/alpine base images
- **Layer Caching**: Order instructions from least to most frequently changing
- **Non-Root User**: Run containers as non-root for security
- **One Process Per Container**: Separate concerns into distinct containers

## Dockerfile Patterns

### Multi-Stage Build
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER node
CMD ["node", "dist/index.js"]
```

### .dockerignore
```
node_modules
.git
*.md
.env
```

## Docker Compose
```yaml
services:
  app:
    build: .
    ports: ["3000:3000"]
    depends_on:
      db: { condition: service_healthy }
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: secret
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
```

## Anti-Patterns
- Using `latest` tag in production
- Storing secrets in images (use environment variables or secrets managers)
- Running as root
- Not using `.dockerignore`
