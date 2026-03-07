---
name: kubernetes-essentials
description: Kubernetes core concepts and deployment patterns. Use when working with kubernetes essentials concepts or setting up related projects.
---

# Kubernetes Essentials

## Core Concepts

- **Pod**: Smallest deployable unit; one or more containers
- **Deployment**: Manages ReplicaSets for rolling updates
- **Service**: Stable network endpoint for accessing pods
- **ConfigMap/Secret**: External configuration injection

## Key Manifests

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  selector:
    matchLabels: { app: api }
  template:
    metadata:
      labels: { app: api }
    spec:
      containers:
      - name: api
        image: myapp:1.0.0
        ports: [{ containerPort: 8080 }]
        resources:
          requests: { memory: "128Mi", cpu: "100m" }
          limits: { memory: "256Mi", cpu: "500m" }
        readinessProbe:
          httpGet: { path: /health, port: 8080 }
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  selector: { app: api }
  ports: [{ port: 80, targetPort: 8080 }]
```

## Best Practices
- Always set resource requests and limits
- Use liveness and readiness probes
- Use namespaces for environment isolation
- Store secrets in external secret managers (not in manifests)
