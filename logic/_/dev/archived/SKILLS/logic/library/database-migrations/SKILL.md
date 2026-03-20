---
name: database-migrations
description: Database migration patterns and best practices. Use when working with database migrations concepts or setting up related projects.
---

# Database Migrations

## Core Principles

- **Version Control**: Every schema change is a numbered migration file
- **Forward-Only**: Prefer new migrations over editing existing ones
- **Backward Compatible**: Changes should not break running application instances
- **Data Migrations Separate**: Keep schema changes and data transformations separate

## Safe Migration Patterns

### Adding a Column
```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
-- Safe: nullable column, no lock on reads
```

### Renaming a Column (Zero-Downtime)
1. Add new column
2. Backfill data from old column
3. Deploy code that writes to both columns
4. Deploy code that reads from new column
5. Drop old column

### Adding an Index Concurrently (PostgreSQL)
```sql
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
-- Does not block writes
```

## Anti-Patterns
- Running migrations in application startup (use separate migration step)
- `ALTER TABLE` with `NOT NULL` and no default on large tables (locks table)
- Dropping columns before all application instances stop reading them
