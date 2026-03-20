---
name: postgresql-advanced
description: PostgreSQL advanced features and patterns. Use when working with postgresql advanced concepts or setting up related projects.
---

# PostgreSQL Advanced

## Key Features

### JSONB Operations
```sql
-- Store and query JSON
CREATE TABLE events (id serial, data jsonb);
INSERT INTO events (data) VALUES ('{"type":"click","x":100}');
SELECT * FROM events WHERE data->>'type' = 'click';
CREATE INDEX idx_events_type ON events USING gin (data);
```

### Common Table Expressions (CTE)
```sql
WITH monthly_revenue AS (
  SELECT date_trunc('month', created_at) AS month, SUM(amount) AS total
  FROM orders GROUP BY 1
)
SELECT month, total, total - LAG(total) OVER (ORDER BY month) AS growth
FROM monthly_revenue;
```

### Window Functions
```sql
SELECT name, department, salary,
  RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank,
  AVG(salary) OVER (PARTITION BY department) AS dept_avg
FROM employees;
```

### Upsert (ON CONFLICT)
```sql
INSERT INTO users (email, name) VALUES ('a@b.com', 'Alice')
ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, updated_at = NOW();
```

## Performance Tips
- Use `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` for detailed plans
- `pg_stat_statements` for identifying slow queries
- Partitioning for tables with millions of rows
- Vacuum and analyze regularly
