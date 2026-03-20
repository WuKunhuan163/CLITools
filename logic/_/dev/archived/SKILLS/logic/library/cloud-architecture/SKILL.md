---
name: cloud-architecture
description: Cloud architecture patterns (AWS/GCP/Azure). Use when working with cloud architecture concepts or setting up related projects.
---

# Cloud Architecture Patterns

## Core Patterns

### Multi-Tier
```
CDN -> Load Balancer -> App Servers -> Database
                                    -> Cache (Redis)
                                    -> Object Storage (S3)
```

### Event-Driven
```
API Gateway -> Lambda -> SQS -> Worker Lambda -> Database
                      -> SNS -> Email/SMS/Webhook
```

### Data Lake
```
Sources -> Ingestion (Kinesis/Pub-Sub) -> Raw Storage (S3/GCS)
        -> Transform (Spark/Dataflow) -> Processed Storage
        -> Analytics (Athena/BigQuery) -> Dashboard
```

## Well-Architected Principles

1. **Operational Excellence**: Automate operations, iterate frequently
2. **Security**: Least privilege, encrypt at rest and in transit
3. **Reliability**: Multi-AZ, auto-scaling, disaster recovery
4. **Performance**: Right-size instances, use caching and CDNs
5. **Cost Optimization**: Reserved instances, spot instances, auto-scaling

## Anti-Patterns
- Single region without disaster recovery plan
- Over-provisioning (use auto-scaling)
- Storing secrets in code or environment variables without a secrets manager
