---
name: svelte-patterns
description: Svelte 5 reactive patterns and runes. Use when working with svelte patterns concepts or setting up related projects.
---

# Svelte Reactive Patterns

## Core Principles

- **Runes**: Use `$state`, `$derived`, `$effect` for explicit reactivity (Svelte 5)
- **Component Composition**: Prefer slots and snippets for flexible layouts
- **Stores**: Use for cross-component state; prefer runes within components
- **Minimal Abstraction**: Svelte compiles away the framework; write less code

## Key Patterns

### State and Derived (Svelte 5)
```svelte
<script>
  let count = $state(0);
  let doubled = $derived(count * 2);
</script>
<button onclick={() => count++}>{count} (doubled: {doubled})</button>
```

### Effects with Cleanup
```svelte
<script>
  let interval = $state(null);
  $effect(() => {
    interval = setInterval(() => count++, 1000);
    return () => clearInterval(interval);
  });
</script>
```

## Anti-Patterns
- Using reactive statements for imperative side effects without cleanup
- Deeply nested component trees instead of using slots
- Overusing stores when local state suffices
