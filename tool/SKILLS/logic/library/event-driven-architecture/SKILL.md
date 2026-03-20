---
name: event-driven-architecture
description: Event-driven architecture patterns with message queues. Use when working with event driven architecture concepts or setting up related projects.
---

# Event-Driven Architecture

## Core Principles

- **Loose Coupling**: Producers don't know about consumers
- **Event Sourcing**: Store state changes as immutable events
- **CQRS**: Separate read and write models for optimization
- **Idempotency**: Consumers must handle duplicate events gracefully

## Event Types

### Domain Events (fact about something that happened)
```json
{ "type": "OrderPlaced", "orderId": "123", "timestamp": "2026-01-01T00:00:00Z" }
```

### Commands (request to do something)
```json
{ "type": "ProcessPayment", "orderId": "123", "amount": 99.99 }
```

## Message Queue Patterns

### Topic/Subscription (Fan-out)
One event, multiple consumers (e.g., Kafka topics, SNS/SQS)

### Work Queue (Competing Consumers)
One message, one consumer (load balancing)

### Dead Letter Queue
Failed messages after max retries go to DLQ for investigation

## Anti-Patterns
- Using events for synchronous request/response patterns
- Not versioning event schemas
- Processing events without idempotency guards
