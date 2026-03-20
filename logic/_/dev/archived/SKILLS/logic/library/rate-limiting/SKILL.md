---
name: rate-limiting
description: Rate limiting and API throttling patterns. Use when working with rate limiting concepts or setting up related projects.
---

# Rate Limiting & Throttling

## Core Principles

- **Protect Resources**: Prevent abuse and ensure fair access
- **Multiple Layers**: Rate limit at API gateway, application, and DB levels
- **Granular Limits**: Per user, per IP, per endpoint
- **Communicate Limits**: Use `X-RateLimit-*` headers

## Algorithms

### Token Bucket
- Tokens added at fixed rate; each request consumes one
- Allows bursts up to bucket capacity
- Most common for API rate limiting

### Sliding Window
- Count requests in rolling time window
- More accurate than fixed windows, avoids boundary spikes

### Leaky Bucket
- Requests queued and processed at fixed rate
- Smooths out traffic; excess requests dropped

## Implementation (Redis)
```python
def is_rate_limited(user_id: str, limit: int = 100, window: int = 60) -> bool:
    key = f"rate:{user_id}"
    current = redis.incr(key)
    if current == 1:
        redis.expire(key, window)
    return current > limit
```

## Response Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1672531200
Retry-After: 30
```
