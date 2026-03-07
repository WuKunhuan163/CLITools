---
name: responsive-design
description: Responsive web design techniques and patterns. Use when working with responsive design concepts or setting up related projects.
---

# Responsive Web Design

## Core Principles

- **Mobile-First**: Write base styles for mobile, add complexity with `min-width` media queries
- **Fluid Layout**: Use relative units (`%`, `rem`, `vw`, `fr`) over fixed `px`
- **Container Queries**: Scope responsive behavior to the component's container
- **Intrinsic Design**: Let content dictate layout using `min()`, `max()`, `clamp()`

## Key Techniques

### Fluid Typography
```css
font-size: clamp(1rem, 0.5rem + 2vw, 2rem);
```

### Responsive Grid
```css
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(300px, 100%), 1fr));
  gap: 1rem;
}
```

### Container Queries
```css
.card-container { container-type: inline-size; }
@container (min-width: 400px) {
  .card { flex-direction: row; }
}
```

## Anti-Patterns
- Using device-specific breakpoints (design for content, not devices)
- Hiding content on mobile with `display: none` (restructure instead)
- Fixed-width layouts that don't adapt
