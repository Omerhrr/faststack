# FastUI

> A high-performance, single-file CDN library for Server-Driven Interactivity (SDI) with FastStack, HTMX, Alpine.js, ECharts, Flowbite, and Tailwind CSS.

[![npm version](https://badge.fury.io/js/fast-ui.svg)](https://badge.fury.io/js/fast-ui)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why FastUI?

Building modern web apps with HTMX + Alpine.js + Tailwind is powerful, but comes with friction:

- ❌ "Why did my Flowbite modal break after HTMX swap?"
- ❌ "How do I reinitialize ECharts in dynamically loaded content?"
- ❌ "Why do I need 5 CDN script tags?"
- ❌ "How do I persist state across HTMX navigation?"

**FastUI solves all of these automatically** with a single CDN include.

## Features

- 🚀 **Zero-Hydration**: Instant interactivity on page load
- 🔄 **Auto-Reinit**: HTMX swaps automatically reinitialize Alpine, Flowbite, and ECharts
- 📦 **Single-Tag Setup**: CSS and JS bundled into one minified file
- 📊 **ECharts Integration**: `x-chart` directive with lazy loading
- 🎨 **Flowbite Integration**: `x-flow` directive for auto-init components
- ⚡ **Lazy Loading**: `x-lazy` directive for on-demand content
- 💾 **Fragment Caching**: Optional in-memory cache for HTMX fragments
- 🌐 **Global State Store**: Alpine store for cross-fragment state

## Quick Start

### CDN (Recommended)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FastUI App</title>
  <!-- FastUI includes everything: Tailwind, Alpine, HTMX -->
  <script src="https://cdn.jsdelivr.net/npm/fast-ui@latest/dist/fast-ui.min.js"></script>
</head>
<body class="bg-gray-100 min-h-screen">
  <div class="container mx-auto p-8">
    <!-- x-chart directive for ECharts -->
    <div x-chart='{
      "title": { "text": "Sales Data" },
      "xAxis": { "type": "category", "data": ["Mon", "Tue", "Wed", "Thu", "Fri"] },
      "yAxis": { "type": "value" },
      "series": [{ "data": [120, 200, 150, 80, 70], "type": "bar" }]
    }' class="h-64 w-full"></div>

    <!-- x-flow directive for Flowbite -->
    <button x-flow="modal" data-modal-target="exampleModal" 
            class="bg-blue-500 text-white px-4 py-2 rounded">
      Open Modal
    </button>

    <!-- x-lazy directive for lazy loading -->
    <div x-lazy data-lazy-src="/partial/content.html" class="h-32 bg-gray-200">
      Loading...
    </div>
  </div>
</body>
</html>
```

### NPM

```bash
npm install fast-ui
```

```javascript
import { createFastUI } from 'fast-ui';

const fastui = createFastUI({
  debug: true,
  cacheEnabled: true,
  cacheTTL: 5 * 60 * 1000, // 5 minutes
});

fastui.init();
```

## Directives

### `x-chart` - ECharts Integration

Create beautiful charts with a single directive:

```html
<!-- Basic chart -->
<div x-chart='{"title": {"text": "My Chart"}, "series": [...]}'></div>

<!-- With lazy loading -->
<div x-chart='{"lazy": true, ...}'></div>

<!-- Responsive chart -->
<div x-chart='{"responsive": true, ...}'></div>

<!-- Auto-refresh from API -->
<div x-chart='{"dataSource": "/api/chart-data", "refreshInterval": 5000}'></div>
```

**Options:**
- `lazy` - Load chart when visible (default: false)
- `responsive` - Resize on window resize (default: true)
- `theme` - ECharts theme name
- `height` / `width` - Chart dimensions
- `dataSource` - API endpoint for chart data
- `refreshInterval` - Auto-refresh interval in ms

### `x-flow` - Flowbite Components

Initialize Flowbite components automatically:

```html
<!-- Single component -->
<div x-flow="modal">...</div>

<!-- Multiple components -->
<div x-flow="accordion,tooltip">...</div>
```

**Supported components:**
- `accordion`
- `carousel`
- `collapse`
- `dropdown`
- `modal`
- `tabs`
- `tooltip`
- `popover`
- `drawer`
- `dismiss`

### `x-lazy` - Lazy Loading

Load content on-demand:

```html
<!-- Load from URL -->
<div x-lazy data-lazy-src="/partial/content.html"></div>

<!-- Load from template -->
<div x-lazy data-lazy-template="my-template"></div>

<!-- Load web component -->
<div x-lazy data-lazy-component="my-component" data-lazy-script="/components/my-component.js"></div>
```

### `x-init-fragment` - State Persistence

Persist Alpine state across HTMX swaps:

```html
<div x-data="{ count: 0 }" x-init-fragment="counter">
  <button @click="count++">Count: <span x-text="count"></span></button>
</div>
```

## HTMX Integration

FastUI automatically reinitializes components after HTMX swaps:

```html
<!-- Before: Flowbite modals would break after swap -->
<div hx-get="/modal-content" hx-target="#modal-container">
  Load Modal
</div>

<!-- After: FastUI auto-reinitializes -->
<!-- Just include FastUI and everything works! -->
```

## Global Store

Share state across fragments:

```javascript
// Set value
FastUI.store.set('user', { name: 'John', role: 'admin' });

// Get value
const user = FastUI.store.get('user');

// Subscribe to changes
FastUI.store.subscribe('user', (value) => {
  console.log('User updated:', value);
});
```

## Fragment Cache

Cache HTMX fragments for faster navigation:

```javascript
// Caching is enabled by default
// Check cached fragment
const cached = FastUI.cache.get('/api/partial');

// Manual caching
FastUI.cache.set('/api/partial', {
  html: '<div>...</div>',
  ttl: 60000, // 1 minute
});
```

## Events

Listen to FastUI events:

```javascript
// FastUI ready
window.addEventListener('fastui:ready', (e) => {
  console.log('FastUI version:', e.detail.version);
});

// Component reinitialized
window.addEventListener('fastui:reinit', (e) => {
  console.log('Reinitialized:', e.detail.target);
});

// Lazy content loaded
window.addEventListener('fastui:lazy:loaded', (e) => {
  console.log('Lazy loaded:', e.detail.element);
});

// Error handling
window.addEventListener('fastui:error', (e) => {
  console.error('Error:', e.detail.status, e.detail.response);
});
```

## API Reference

### `FastUI.init()`

Initialize FastUI. Called automatically on DOM ready.

### `FastUI.reinit(el)`

Manually reinitialize components in an element.

```javascript
FastUI.reinit(document.getElementById('my-container'));
```

### `FastUI.registerDirective(name, directive)`

Register a custom Alpine directive.

```javascript
FastUI.registerDirective('my-directive', {
  name: 'my-directive',
  callback: (el, value) => {
    // Directive logic
  },
});
```

### `FastUI.registerPlugin(name, plugin)`

Register a custom plugin.

```javascript
FastUI.registerPlugin('my-plugin', {
  name: 'my-plugin',
  install: (api) => {
    // Plugin logic
  },
});
```

### `FastUI.lazyLoad(module)`

Lazy load a module.

```javascript
await FastUI.lazyLoad('echarts');
await FastUI.lazyLoad('flowbite');
```

## Development

```bash
# Install dependencies
npm install

# Development build with watch
npm run dev

# Production build
npm run build

# Run tests
npm test

# Type check
npm run typecheck
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## Links

- [FastStack Framework](https://github.com/Omerhrr/faststack)
- [HTMX](https://htmx.org/)
- [Alpine.js](https://alpinejs.dev/)
- [ECharts](https://echarts.apache.org/)
- [Flowbite](https://flowbite.com/)
- [Tailwind CSS](https://tailwindcss.com/)
