---
name: state-management-patterns
description: Frontend state management patterns and strategies. Use when working with state management patterns concepts or setting up related projects.
---

# State Management Patterns

## Core Principles

- **Colocate State**: Keep state near where it's consumed
- **Single Source of Truth**: Each piece of state should have one owner
- **Derived State Over Synced State**: Compute values rather than duplicating
- **Server State vs Client State**: Use different tools for each (React Query for server, Zustand/Redux for client)

## Patterns by Complexity

### Local State (useState/ref)
Best for: form inputs, toggles, UI-only state

### Lifted State
Best for: sibling components sharing data; lift to nearest common ancestor

### Context/Provide-Inject
Best for: theme, auth, locale -- rarely changing, widely consumed values

### External Store (Redux/Zustand/Pinia)
Best for: complex client state with many updaters, undo/redo, devtools

### Server State (React Query/SWR/TanStack Query)
Best for: cached API data with refetching, optimistic updates, pagination

## Anti-Patterns
- Global state for everything (causes unnecessary re-renders)
- Storing server-fetched data in Redux instead of a query cache
- Using state for values derivable from props/other state
