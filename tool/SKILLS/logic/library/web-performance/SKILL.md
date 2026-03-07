---
name: web-performance
description: Web performance optimization techniques. Use when working with web performance concepts or setting up related projects.
---

# Web Performance Optimization

## Core Web Vitals

- **LCP** (Largest Contentful Paint): < 2.5s -- optimize images, fonts, critical CSS
- **INP** (Interaction to Next Paint): < 200ms -- minimize main thread work
- **CLS** (Cumulative Layout Shift): < 0.1 -- reserve space for dynamic content

## Key Techniques

### Image Optimization
```html
<img src="photo.webp" width="800" height="600" loading="lazy"
     srcset="photo-400.webp 400w, photo-800.webp 800w" sizes="(max-width: 600px) 400px, 800px" />
```

### Critical CSS
Inline above-the-fold CSS; defer the rest.

### Resource Hints
```html
<link rel="preconnect" href="https://api.example.com" />
<link rel="preload" href="/fonts/main.woff2" as="font" crossorigin />
<link rel="prefetch" href="/next-page.html" />
```

### Bundle Optimization
- Code splitting by route
- Tree shaking dead code
- Dynamic imports for heavy libraries
- Compression: Brotli > gzip

## Measurement Tools
- Lighthouse (Chrome DevTools)
- WebPageTest.org
- Chrome User Experience Report (CrUX)
- Performance Observer API for real user monitoring

## Anti-Patterns
- Loading all JavaScript upfront
- Unoptimized images (use WebP/AVIF, proper sizing)
- Render-blocking CSS/JS in `<head>`
- No caching headers on static assets
