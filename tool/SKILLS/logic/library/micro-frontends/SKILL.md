---
name: micro-frontends
description: Micro-frontend architecture patterns. Use when working with micro frontends concepts or setting up related projects.
---

# Micro-Frontends Architecture

## Core Principles

- **Independent Deployment**: Each micro-frontend deploys separately
- **Technology Agnostic**: Teams can use different frameworks
- **Isolation**: Avoid shared runtime state; communicate via events/APIs
- **Shared Nothing by Default**: Only share what's explicitly designed to be shared

## Integration Approaches

### Module Federation (Webpack 5)
```js
new ModuleFederationPlugin({
  name: 'app_shell',
  remotes: { dashboard: 'dashboard@/remoteEntry.js' },
  shared: ['react', 'react-dom'],
});
```

### Web Components Integration
Each team wraps their app in a custom element for framework isolation.

### Server-Side Composition
Assemble fragments on the server (e.g., Podium, Piral).

## Communication Patterns
- **Custom Events**: `window.dispatchEvent(new CustomEvent('navigate', { detail }))`
- **URL/Query Params**: Shared routing state
- **Shared Event Bus**: Lightweight pub/sub

## Anti-Patterns
- Sharing a single Redux store across micro-frontends
- Tightly coupling micro-frontends via direct imports
- Duplicating heavy dependencies without shared module federation
