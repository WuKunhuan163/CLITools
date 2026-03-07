---
name: monitoring-observability
description: Application monitoring and observability patterns. Use when working with monitoring observability concepts or setting up related projects.
---

# Monitoring & Observability

## Three Pillars

### 1. Metrics (quantitative)
- **RED**: Rate, Errors, Duration (for services)
- **USE**: Utilization, Saturation, Errors (for resources)
- Tools: Prometheus, Grafana, Datadog

### 2. Logs (qualitative)
- Structured JSON logging
- Correlation IDs across services
- Tools: ELK Stack, Loki, CloudWatch

### 3. Traces (causal)
- Distributed tracing across microservices
- Span context propagation
- Tools: Jaeger, Zipkin, OpenTelemetry

## OpenTelemetry (Standard)
```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order.id", order_id)
    result = process(order_id)
```

## Alerting Best Practices
- Alert on symptoms (error rate > 1%), not causes (CPU > 80%)
- Use severity levels: critical (page), warning (ticket), info (log)
- Avoid alert fatigue: only alert on actionable conditions
- Include runbook links in alerts
