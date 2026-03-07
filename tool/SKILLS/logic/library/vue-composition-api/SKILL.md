---
name: vue-composition-api
description: Vue 3 Composition API patterns. Use when working with vue composition api concepts or setting up related projects.
---

# Vue 3 Composition API

## Core Principles

- **Composables**: Extract reusable logic into `use`-prefixed functions
- **Reactivity**: Use `ref()` for primitives, `reactive()` for objects
- **Script Setup**: Prefer `<script setup>` for concise component definitions
- **Provide/Inject**: Use for deep prop drilling avoidance

## Key Patterns

### Composable
```ts
export function useCounter(initial = 0) {
  const count = ref(initial);
  const increment = () => count.value++;
  const decrement = () => count.value--;
  return { count, increment, decrement };
}
```

### Computed Properties
```ts
const fullName = computed(() => `${firstName.value} ${lastName.value}`);
```

### Watchers with Cleanup
```ts
watchEffect((onCleanup) => {
  const controller = new AbortController();
  fetch(url.value, { signal: controller.signal });
  onCleanup(() => controller.abort());
});
```

## Anti-Patterns
- Destructuring reactive objects (breaks reactivity; use `toRefs`)
- Using `reactive()` for primitives
- Not using `unref()` when accepting both ref and plain values in composables
