---
name: react-hooks-patterns
description: React Hooks patterns and best practices. Use when working with react hooks patterns concepts or setting up related projects.
---

# React Hooks Patterns

## Core Principles

- **Rules of Hooks**: Only call hooks at the top level; never inside loops, conditions, or nested functions
- **Custom Hooks**: Extract reusable logic into `use`-prefixed functions
- **Dependency Arrays**: Always specify exact dependencies in `useEffect`, `useMemo`, `useCallback`
- **State Colocation**: Keep state as close as possible to where it's used

## Key Patterns

### Derived State (avoid redundant state)
```jsx
// Bad: syncing state
const [items, setItems] = useState([]);
const [count, setCount] = useState(0);

// Good: derive from source of truth
const count = items.length;
```

### Custom Hook for Data Fetching
```jsx
function useApi(url) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then(res => res.json())
      .then(d => { if (!cancelled) setData(d); })
      .catch(e => { if (!cancelled) setError(e); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [url]);

  return { data, error, loading };
}
```

## Anti-Patterns
- Using `useEffect` for state synchronization (use derived state instead)
- Missing cleanup in effects that create subscriptions
- Over-memoizing with `useMemo`/`useCallback` without profiling first
