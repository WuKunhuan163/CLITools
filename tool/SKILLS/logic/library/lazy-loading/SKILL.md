---
name: lazy-loading
description: Lazy loading and code splitting patterns. Use when working with lazy loading concepts or setting up related projects.
---

# Lazy Loading & Code Splitting

## Core Principles

- **Load What's Needed**: Defer loading of off-screen/non-critical resources
- **Route-Based Splitting**: Each route loads its own bundle
- **Component-Level Splitting**: Heavy components load on demand
- **Intersection Observer**: Load content when it enters viewport

## Patterns

### React Lazy Loading
```tsx
const HeavyChart = React.lazy(() => import('./HeavyChart'));

function Dashboard() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyChart />
    </Suspense>
  );
}
```

### Image Lazy Loading
```html
<img src="photo.jpg" loading="lazy" width="800" height="600" />
```

### Intersection Observer
```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      loadContent(entry.target);
      observer.unobserve(entry.target);
    }
  });
});
observer.observe(document.querySelector('.lazy-section'));
```

### Dynamic Import
```js
button.addEventListener('click', async () => {
  const { processData } = await import('./heavy-processor.js');
  processData(input);
});
```

## Anti-Patterns
- Lazy loading above-the-fold content (hurts LCP)
- Too many small chunks (overhead of network requests)
- Not providing loading states for lazy components
