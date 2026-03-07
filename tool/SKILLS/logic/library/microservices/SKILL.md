---
name: microservices
description: Microservices architecture patterns and best practices. Use when working with microservices concepts or setting up related projects.
---

# Microservices Architecture

## Core Principles

- **Single Responsibility**: Each service owns one bounded context
- **Database Per Service**: No shared databases between services
- **API Gateway**: Single entry point for external clients
- **Eventual Consistency**: Accept that distributed state takes time to converge

## Communication Patterns

### Synchronous (REST/gRPC)
- Use for queries needing immediate response
- Implement circuit breakers (retry, timeout, fallback)
- gRPC for internal service-to-service (efficient binary protocol)

### Asynchronous (Events/Messages)
- Use for commands that don't need immediate response
- Event-driven: publish domain events (OrderCreated, UserRegistered)
- Message queues: RabbitMQ, Kafka, SQS for reliable delivery

## Resilience Patterns

### Circuit Breaker
States: Closed (normal) -> Open (fail fast) -> Half-Open (test recovery)

### Saga Pattern
For distributed transactions across services:
- Choreography: Each service publishes events, others react
- Orchestration: Central coordinator manages the workflow

## Anti-Patterns
- Distributed monolith (services tightly coupled via synchronous calls)
- Shared database between services
- No service discovery or load balancing
