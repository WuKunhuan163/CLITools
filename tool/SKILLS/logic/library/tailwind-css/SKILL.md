---
name: tailwind-css
description: Tailwind CSS utility-first patterns and best practices. Use when working with tailwind css concepts or setting up related projects.
---

# Tailwind CSS Best Practices

## Core Principles

- **Utility-First**: Compose styles from atomic utility classes
- **Extract Components**: Use `@apply` or component abstractions for repeated patterns
- **Design Tokens**: Extend `theme` in `tailwind.config.js` for custom values
- **Purge Unused**: Ensure content paths are configured for tree-shaking

## Key Patterns

### Responsive Design
```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
```

### Dark Mode
```html
<div class="bg-white dark:bg-gray-900 text-black dark:text-white">
```

### Custom Plugin
```js
// tailwind.config.js
plugins: [
  function({ addUtilities }) {
    addUtilities({ '.text-balance': { 'text-wrap': 'balance' } });
  }
]
```

## Anti-Patterns
- Overusing `@apply` to recreate traditional CSS (defeats the purpose)
- Extremely long class lists without component extraction
- Not configuring `content` paths (all utilities get purged)
