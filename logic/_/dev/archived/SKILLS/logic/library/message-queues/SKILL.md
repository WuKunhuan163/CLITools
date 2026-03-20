---
name: message-queues
description: Message queue patterns (RabbitMQ, Kafka, SQS). Use when working with message queues concepts or setting up related projects.
---

# Message Queue Patterns

## Queue vs Pub/Sub

### Work Queue (Point-to-Point)
- One message consumed by exactly one consumer
- Use for: task distribution, job processing
- Tools: RabbitMQ, SQS, Celery

### Pub/Sub (Fan-Out)
- One message received by all subscribers
- Use for: event notification, data replication
- Tools: Kafka topics, SNS, Redis Pub/Sub

## Kafka Patterns

### Producer
```python
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='localhost:9092')
producer.send('orders', key=b'order-1', value=json.dumps(order).encode())
```

### Consumer Group
```python
consumer = KafkaConsumer('orders', group_id='order-processors',
                          bootstrap_servers='localhost:9092')
for message in consumer:
    process_order(json.loads(message.value))
```

## Reliability Patterns

### At-Least-Once Delivery
- Acknowledge after processing (not before)
- Consumer must be idempotent

### Dead Letter Queue
- Failed messages after N retries go to DLQ
- Monitor DLQ for investigation

### Backpressure
- Consumer signals producer to slow down
- Use bounded queues or rate limiting

## Anti-Patterns
- Processing messages without idempotency
- No monitoring on queue depth/consumer lag
- Synchronous processing in message handlers
