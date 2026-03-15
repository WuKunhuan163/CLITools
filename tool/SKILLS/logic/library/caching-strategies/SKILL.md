---
name: caching-strategies
description: Caching patterns for backend applications. Use when working with caching strategies concepts or setting up related projects.
---

# Caching Strategies

## Core Principles

- **Cache Invalidation**: The hardest problem; plan your strategy upfront
- **Cache Aside (Lazy Loading)**: Application checks cache, falls back to DB, populates cache
- **Write Through**: Write to cache and DB simultaneously
- **TTL-Based Expiry**: Set appropriate time-to-live for freshness requirements

## Patterns

### Cache Aside
```python
def get_user(user_id):
    cached = redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    user = db.query(User).get(user_id)
    redis.setex(f"user:{user_id}", 3600, json.dumps(user))
    return user
```

### Cache Stampede Prevention
```python
def get_with_lock(key, ttl, compute_fn):
    value = cache.get(key)
    if value is not None:
        return value
    lock = cache.lock(f"lock:{key}", timeout=5)
    if lock.acquire(blocking=True):
        try:
            value = cache.get(key)  # double-check
            if value is None:
                value = compute_fn()
                cache.setex(key, ttl, value)
        finally:
            lock.release()
    return value
```

## Cache Layers
1. **Browser Cache**: HTTP headers (Cache-Control, ETag)
2. **CDN**: Static assets, edge caching
3. **Application Cache**: Redis/Memcached
4. **Database Cache**: Query cache, materialized views
