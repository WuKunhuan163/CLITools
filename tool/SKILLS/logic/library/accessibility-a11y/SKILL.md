---
name: accessibility-a11y
description: Web accessibility (a11y) guidelines and implementation. Use when working with accessibility a11y concepts or setting up related projects.
---

# Web Accessibility (a11y)

## Core Principles

- **Semantic HTML**: Use correct elements (`button`, `nav`, `main`, `article`) over generic `div`/`span`
- **Keyboard Navigation**: All interactive elements must be operable via keyboard
- **ARIA When Needed**: Use ARIA attributes only when native HTML semantics are insufficient
- **Color Contrast**: Maintain minimum 4.5:1 ratio for normal text, 3:1 for large text

## Key Patterns

### Accessible Form
```html
<label for="email">Email address</label>
<input id="email" type="email" aria-describedby="email-help" required />
<span id="email-help">We'll never share your email.</span>
```

### Skip Navigation Link
```html
<a href="#main-content" class="sr-only focus:not-sr-only">Skip to content</a>
```

### Live Regions for Dynamic Content
```html
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>
```

## Testing Checklist
- Tab through entire page; focus order must be logical
- Screen reader testing (VoiceOver on Mac, NVDA on Windows)
- axe-core or Lighthouse accessibility audit
- Test with browser zoom at 200%
