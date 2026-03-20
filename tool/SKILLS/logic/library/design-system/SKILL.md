---
name: design-system
description: Design system creation and component library patterns. Use when working with design system concepts or setting up related projects.
---

# Design System Development

## Core Principles

- **Tokens**: Define primitive values (colors, spacing, typography) as tokens
- **Components**: Build from tokens; composable and accessible
- **Documentation**: Every component needs usage examples and guidelines
- **Versioning**: Semantic versioning for breaking changes

## Design Tokens
```json
{
  "color": {
    "primary": { "50": "#eff6ff", "500": "#3b82f6", "900": "#1e3a8a" },
    "semantic": { "success": "{color.green.500}", "error": "{color.red.500}" }
  },
  "spacing": { "xs": "4px", "sm": "8px", "md": "16px", "lg": "24px" },
  "typography": {
    "heading": { "fontSize": "24px", "fontWeight": "700", "lineHeight": "1.2" }
  }
}
```

## Component API Design
```tsx
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  children: React.ReactNode;
}
```

## Documentation (Storybook)
```tsx
export default { title: 'Components/Button', component: Button };
export const Primary = { args: { variant: 'primary', children: 'Click me' } };
export const Loading = { args: { variant: 'primary', isLoading: true, children: 'Saving' } };
```

## Best Practices
- Start with tokens and primitives before building components
- Every component must meet WCAG 2.1 AA accessibility standards
- Use compound components for flexible APIs
- Provide both controlled and uncontrolled variants
