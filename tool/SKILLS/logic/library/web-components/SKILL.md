---
name: web-components
description: Web Components with Custom Elements and Shadow DOM. Use when working with web components concepts or setting up related projects.
---

# Web Components

## Core Principles

- **Encapsulation**: Shadow DOM isolates styles and markup
- **Reusability**: Framework-agnostic; works everywhere HTML works
- **Lifecycle**: Use `connectedCallback`, `disconnectedCallback`, `attributeChangedCallback`
- **Slots**: Allow content projection via `<slot>` elements

## Key Pattern

### Custom Element
```js
class MyCard extends HTMLElement {
  static get observedAttributes() { return ['title']; }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
  }

  attributeChangedCallback() {
    this.render();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>:host { display: block; border: 1px solid #ccc; padding: 1rem; }</style>
      <h2>${this.getAttribute('title') || ''}</h2>
      <slot></slot>
    `;
  }
}
customElements.define('my-card', MyCard);
```

## When to Use
- Shared component libraries across frameworks
- Micro-frontend boundaries
- Design system primitives
