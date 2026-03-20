---
name: mongodb-patterns
description: MongoDB schema design and query patterns. Use when working with mongodb patterns concepts or setting up related projects.
---

# MongoDB Schema Design

## Core Principles

- **Data That's Accessed Together Should Be Stored Together**: Embed for 1:1 and 1:few
- **Reference for 1:many and many:many**: Use `$lookup` (JOIN) for large/independent collections
- **Schema Validation**: Enforce structure with JSON Schema validators
- **Indexes**: Create compound indexes matching your query patterns

## Embedding vs Referencing

### Embed (denormalize)
```json
{
  "_id": "user1",
  "name": "Alice",
  "addresses": [
    { "street": "123 Main", "city": "Portland" }
  ]
}
```
Best for: data always accessed together, rarely updated independently

### Reference (normalize)
```json
{ "_id": "order1", "user_id": "user1", "items": ["item1", "item2"] }
```
Best for: independent entities, many-to-many, large/growing arrays

## Aggregation Pipeline
```js
db.orders.aggregate([
  { $match: { status: "completed" } },
  { $group: { _id: "$customer_id", total: { $sum: "$amount" } } },
  { $sort: { total: -1 } },
  { $limit: 10 }
]);
```

## Anti-Patterns
- Unbounded array growth (use bucketing pattern)
- No indexes on frequently queried fields
- Using MongoDB as a relational database with excessive `$lookup`s
