---
name: graphql-development
description: GraphQL schema design and resolver patterns. Use when working with graphql development concepts or setting up related projects.
---

# GraphQL Development

## Core Principles

- **Schema-First Design**: Define types before implementing resolvers
- **N+1 Prevention**: Use DataLoader for batched database queries
- **Pagination**: Use Relay-style cursor pagination for lists
- **Error Handling**: Use union types for expected errors, throw for unexpected

## Schema Design

```graphql
type Query {
  user(id: ID!): User
  users(first: Int, after: String): UserConnection!
}

type User {
  id: ID!
  name: String!
  posts(first: Int): PostConnection!
}

type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
}
```

## DataLoader Pattern
```ts
const userLoader = new DataLoader(async (ids: string[]) => {
  const users = await db.user.findMany({ where: { id: { in: ids } } });
  return ids.map(id => users.find(u => u.id === id));
});
```

## Anti-Patterns
- Deeply nested queries without depth limiting
- Exposing database schema directly as GraphQL schema
- Not implementing query complexity analysis
