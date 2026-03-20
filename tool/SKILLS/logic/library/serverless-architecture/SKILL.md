---
name: serverless-architecture
description: Serverless architecture patterns (AWS Lambda, Cloud Functions). Use when working with serverless architecture concepts or setting up related projects.
---

# Serverless Architecture

## Core Principles

- **Stateless Functions**: Each invocation is independent; use external storage for state
- **Cold Starts**: Minimize by keeping functions small and dependencies lean
- **Event-Driven**: Functions triggered by events (HTTP, queue, schedule, storage)
- **Pay-Per-Use**: Cost scales with actual invocations, not provisioned capacity

## Key Patterns

### API Handler (AWS Lambda)
```python
def handler(event, context):
    path = event['path']
    method = event['httpMethod']
    body = json.loads(event.get('body', '{}'))
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'message': 'success'})
    }
```

### Fan-Out Pattern
- API Gateway -> Lambda -> SQS -> Multiple Lambda consumers
- Scales horizontally with queue depth

### Scheduled Jobs
```yaml
functions:
  cleanup:
    handler: cleanup.handler
    events:
      - schedule: rate(1 hour)
```

## Anti-Patterns
- Functions that run longer than 15 minutes (use Step Functions)
- Tight coupling between functions
- Not setting concurrency limits (runaway costs)
- Synchronous chains of Lambda calls
