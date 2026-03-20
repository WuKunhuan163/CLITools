---
name: sql-optimization
description: SQL query optimization techniques. Use when working with sql optimization concepts or setting up related projects.
---

# SQL Query Optimization

## Core Principles

- **EXPLAIN ANALYZE**: Always check query execution plans before optimizing
- **Index Design**: Create indexes for WHERE, JOIN, ORDER BY columns
- **Avoid SELECT ***: Only fetch needed columns
- **Batch Operations**: Use bulk inserts/updates instead of row-by-row

## Key Techniques

### Index Strategy
```sql
-- Composite index for common query pattern
CREATE INDEX idx_orders_customer_date ON orders(customer_id, created_at DESC);

-- Partial index for common filter
CREATE INDEX idx_active_users ON users(email) WHERE status = 'active';
```

### Avoiding N+1 with JOINs
```sql
-- Bad: N separate queries in application loop
-- Good: single query with JOIN
SELECT o.*, c.name FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.status = 'pending';
```

### Pagination with Cursor
```sql
-- Keyset pagination (efficient for large datasets)
SELECT * FROM posts WHERE id > :last_id ORDER BY id LIMIT 20;
```

## Common Pitfalls
- Using functions on indexed columns in WHERE (`WHERE YEAR(created_at) = 2026`)
- Missing indexes on foreign key columns
- Correlated subqueries when JOINs work
- Not using connection pooling
