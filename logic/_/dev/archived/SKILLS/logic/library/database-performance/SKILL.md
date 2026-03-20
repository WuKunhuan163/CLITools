---
name: database-performance
description: Database performance tuning techniques. Use when working with database performance concepts or setting up related projects.
---

# Database Performance

## Key Optimization Areas

### Indexing Strategy
```sql
-- Check if index is used
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 123;

-- Composite index for common query
CREATE INDEX idx_orders_status_date ON orders(status, created_at DESC);

-- Covering index (includes all needed columns)
CREATE INDEX idx_users_email_name ON users(email) INCLUDE (name);
```

### Query Optimization
```sql
-- Bad: correlated subquery
SELECT * FROM orders WHERE amount > (SELECT AVG(amount) FROM orders);

-- Good: CTE or window function
WITH avg_amount AS (SELECT AVG(amount) AS avg FROM orders)
SELECT o.* FROM orders o, avg_amount WHERE o.amount > avg_amount.avg;
```

### Connection Pooling
```python
# SQLAlchemy
engine = create_engine(url, pool_size=20, max_overflow=10, pool_timeout=30)
```

### Read Replicas
- Route reads to replicas, writes to primary
- Accept slight replication lag for read queries

## Monitoring Queries
```sql
-- PostgreSQL: find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 20;
```

## Anti-Patterns
- Missing indexes on foreign keys and WHERE clause columns
- `SELECT *` when only specific columns needed
- Not using connection pooling (opening new connection per request)
- N+1 queries in application code
