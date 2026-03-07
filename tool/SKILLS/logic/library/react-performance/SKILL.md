---
name: react-performance
description: React performance optimization techniques. Use when working with react performance concepts or setting up related projects.
---

# React Performance Optimization

## Core Principles

- **Measure First**: Use React DevTools Profiler before optimizing
- **Minimize Re-renders**: Only re-render components that actually changed
- **Virtualize Long Lists**: Use `react-window` or `react-virtuoso` for large datasets
- **Code Split**: Use `React.lazy()` and `Suspense` for route-based splitting

## Key Techniques

### React.memo for Expensive Components
```jsx
const ExpensiveList = React.memo(({ items }) => (
  <ul>{items.map(item => <li key={item.id}>{item.name}</li>)}</ul>
));
```

### useCallback for Stable References
```jsx
const handleClick = useCallback((id) => {
  setItems(prev => prev.filter(item => item.id !== id));
}, []);
```

### Lazy Loading Routes
```jsx
const Dashboard = React.lazy(() => import('./Dashboard'));
<Suspense fallback={<Spinner />}>
  <Dashboard />
</Suspense>
```

## Anti-Patterns
- Premature optimization without profiling
- Putting all state in a single context (causes full tree re-renders)
- Creating new objects/arrays in render without memoization
