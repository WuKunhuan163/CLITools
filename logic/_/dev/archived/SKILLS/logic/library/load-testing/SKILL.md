---
name: load-testing
description: Load testing and performance benchmarking. Use when working with load testing concepts or setting up related projects.
---

# Load Testing

## Core Concepts

- **Throughput**: Requests per second the system handles
- **Latency**: Response time (p50, p95, p99 percentiles)
- **Saturation**: At what load does the system degrade?
- **Error Rate**: Percentage of failed requests under load

## Test Types

1. **Smoke Test**: Minimal load to verify system works
2. **Load Test**: Expected normal traffic
3. **Stress Test**: Beyond expected capacity to find breaking point
4. **Soak Test**: Sustained load over hours (memory leaks, connection exhaustion)

## k6 Example
```js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // ramp up
    { duration: '5m', target: 50 },   // sustain
    { duration: '1m', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95th percentile < 500ms
    http_req_failed: ['rate<0.01'],    // <1% error rate
  },
};

export default function () {
  const res = http.get('https://api.example.com/users');
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}
```

## Key Metrics to Track
- Response time percentiles (p50, p95, p99)
- Error rate under increasing load
- Resource utilization (CPU, memory, connections)
- Queue depth and processing lag
