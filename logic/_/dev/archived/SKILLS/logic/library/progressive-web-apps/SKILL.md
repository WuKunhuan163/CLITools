---
name: progressive-web-apps
description: PWA development patterns with service workers and offline support. Use when working with progressive web apps concepts or setting up related projects.
---

# Progressive Web Apps (PWA)

## Core Principles

- **Reliable**: Load instantly via service worker caching, even offline
- **Fast**: Respond quickly with cached resources and background sync
- **Installable**: Provide `manifest.json` with proper icons and metadata
- **Progressive Enhancement**: Works without service worker; enhanced with it

## Key Components

### Web App Manifest
```json
{
  "name": "My App",
  "short_name": "App",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#1a1a2e",
  "icons": [{ "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" }]
}
```

### Service Worker Cache Strategy
```js
// Cache-first for static assets
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
```

### Background Sync
```js
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-queue') {
    event.waitUntil(flushQueue());
  }
});
```

## Caching Strategies
- **Cache First**: Static assets (images, fonts, CSS)
- **Network First**: API responses needing freshness
- **Stale While Revalidate**: Content that can be slightly stale
