---
name: typescript-fundamentals
description: TypeScript type system patterns and best practices. Use when working with typescript fundamentals concepts or setting up related projects.
---

# TypeScript Fundamentals

## Core Principles

- **Strict Mode**: Always enable `strict: true` in `tsconfig.json`
- **Inference Over Annotation**: Let TypeScript infer types when obvious
- **Discriminated Unions**: Prefer over broad types for state modeling
- **Utility Types**: Use `Partial`, `Required`, `Pick`, `Omit`, `Record` effectively

## Key Patterns

### Discriminated Union
```ts
type Result<T> =
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

function handle(result: Result<User>) {
  if (result.status === 'success') {
    console.log(result.data.name); // narrowed
  }
}
```

### Generic Constraints
```ts
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
```

### Branded Types
```ts
type UserId = string & { readonly __brand: 'UserId' };
function createUserId(id: string): UserId { return id as UserId; }
```

## Anti-Patterns
- Using `any` instead of `unknown` for truly unknown types
- Type assertions (`as`) instead of type guards
- Overly complex generics that reduce readability
