---
name: redis-patterns
description: Redis data structures and caching patterns. Use when working with redis patterns concepts or setting up related projects.
---

# Redis Patterns

## Core Data Structures

### Strings
```redis
SET user:1:name "Alice" EX 3600   -- with 1-hour TTL
GET user:1:name
INCR page:views                    -- atomic counter
```

### Hashes
```redis
HSET user:1 name "Alice" email "a@b.com"
HGETALL user:1
```

### Sorted Sets (leaderboards, rate limiting)
```redis
ZADD leaderboard 100 "player1" 200 "player2"
ZREVRANGE leaderboard 0 9 WITHSCORES    -- top 10
```

### Lists (queues)
```redis
LPUSH queue:tasks '{"type":"email"}'
BRPOP queue:tasks 30                     -- blocking pop with timeout
```

## Patterns

### Distributed Lock
```redis
SET lock:resource unique_value NX EX 30   -- acquire
-- critical section
DEL lock:resource                         -- release (with Lua for safety)
```

### Pub/Sub
```redis
SUBSCRIBE channel:notifications
PUBLISH channel:notifications "new order"
```

## Anti-Patterns
- Using Redis as primary database (it's volatile by default)
- Storing large blobs (>1MB) in Redis
- Not setting TTLs (memory grows unbounded)
