/**
 * FastUI Tailwind CSS Injection
 * Dynamically injects Tailwind CSS if not already present
 */

import { debugLog, loadScript } from '../utils/helpers';

/**
 * Tailwind CSS CDN URL
 */
const TAILWIND_CDN = 'https://cdn.tailwindcss.com';

/**
 * Flowbite CSS CDN URL
 */
const FLOWBITE_CSS_CDN = 'https://cdn.jsdelivr.net/npm/flowbite@2.2.0/dist/flowbite.min.css';

/**
 * Flowbite JS CDN URL
 */
const FLOWBITE_JS_CDN = 'https://cdn.jsdelivr.net/npm/flowbite@2.2.0/dist/flowbite.min.js';

/**
 * ECharts CDN URL
 */
const ECHARTS_CDN = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';

/**
 * Alpine.js CDN URL
 */
const ALPINE_CDN = 'https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js';

/**
 * HTMX CDN URL
 */
const HTMX_CDN = 'https://cdn.jsdelivr.net/npm/htmx.org@1.9.10/dist/htmx.min.js';

/**
 * Check if Tailwind CSS is loaded
 */
export function hasTailwind(): boolean {
  // Check for Tailwind script
  const scripts = document.querySelectorAll('script[src*="tailwind"]');
  if (scripts.length > 0) return true;

  // Check for Tailwind styles
  const styles = document.querySelectorAll('style');
  for (const style of styles) {
    if (style.textContent?.includes('tailwind') || style.textContent?.includes('--tw-')) {
      return true;
    }
  }

  return false;
}

/**
 * Check if a script is already loaded
 */
function isScriptLoaded(src: string): boolean {
  return document.querySelector(`script[src*="${src}"]`) !== null;
}

/**
 * Check if a stylesheet is already loaded
 */
function isStyleLoaded(href: string): boolean {
  return document.querySelector(`link[href*="${href}"]`) !== null;
}

/**
 * Load Tailwind CSS dynamically
 */
export async function loadTailwind(): Promise<void> {
  if (hasTailwind()) {
    debugLog('Tailwind already loaded');
    return;
  }

  try {
    await loadScript(TAILWIND_CDN);
    debugLog('Tailwind CSS loaded');
  } catch (e) {
    console.error('[FastUI] Failed to load Tailwind CSS:', e);
    throw e;
  }
}

/**
 * Load Flowbite CSS
 */
async function loadFlowbiteCSS(): Promise<void> {
  if (isStyleLoaded('flowbite')) {
    debugLog('Flowbite CSS already loaded');
    return;
  }

  return new Promise((resolve, reject) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = FLOWBITE_CSS_CDN;
    link.onload = () => {
      debugLog('Flowbite CSS loaded');
      resolve();
    };
    link.onerror = () => reject(new Error('Failed to load Flowbite CSS'));
    document.head.appendChild(link);
  });
}

/**
 * Load Flowbite JS
 */
async function loadFlowbiteJS(): Promise<void> {
  if (isScriptLoaded('flowbite')) {
    debugLog('Flowbite JS already loaded');
    return;
  }

  try {
    await loadScript(FLOWBITE_JS_CDN);
    debugLog('Flowbite JS loaded');
  } catch (e) {
    console.error('[FastUI] Failed to load Flowbite JS:', e);
    throw e;
  }
}

/**
 * Load Flowbite (CSS + JS)
 */
export async function loadFlowbite(): Promise<void> {
  await Promise.all([loadFlowbiteCSS(), loadFlowbiteJS()]);
}

/**
 * Load ECharts
 */
export async function loadECharts(): Promise<void> {
  if (isScriptLoaded('echarts') || typeof window.echarts !== 'undefined') {
    debugLog('ECharts already loaded');
    return;
  }

  try {
    await loadScript(ECHARTS_CDN);
    debugLog('ECharts loaded');
  } catch (e) {
    console.error('[FastUI] Failed to load ECharts:', e);
    throw e;
  }
}

/**
 * Load Alpine.js
 */
export async function loadAlpine(): Promise<void> {
  if (isScriptLoaded('alpinejs') || typeof window.Alpine !== 'undefined') {
    debugLog('Alpine.js already loaded');
    return;
  }

  try {
    await loadScript(ALPINE_CDN);
    debugLog('Alpine.js loaded');
  } catch (e) {
    console.error('[FastUI] Failed to load Alpine.js:', e);
    throw e;
  }
}

/**
 * Load HTMX
 */
export async function loadHTMX(): Promise<void> {
  if (isScriptLoaded('htmx') || typeof window.htmx !== 'undefined') {
    debugLog('HTMX already loaded');
    return;
  }

  try {
    await loadScript(HTMX_CDN);
    debugLog('HTMX loaded');
  } catch (e) {
    console.error('[FastUI] Failed to load HTMX:', e);
    throw e;
  }
}

/**
 * Load all dependencies
 */
export async function loadAllDependencies(): Promise<void> {
  debugLog('Loading all dependencies...');

  await Promise.all([
    loadTailwind(),
    loadAlpine(),
    loadHTMX(),
  ]);

  // Load optional dependencies
  try {
    await loadFlowbite();
  } catch {
    debugLog('Flowbite not loaded (optional)');
  }

  try {
    await loadECharts();
  } catch {
    debugLog('ECharts not loaded (optional)');
  }

  debugLog('All dependencies loaded');
}

/**
 * Configure Tailwind with custom config
 */
export function configureTailwind(config: object): void {
  if (typeof (window as unknown as { tailwind?: { config?: (config: object) => void } }).tailwind?.config === 'function') {
    (window as unknown as { tailwind: { config: (config: object) => void } }).tailwind.config(config);
    debugLog('Tailwind configured', config);
  } else {
    console.warn('[FastUI] Tailwind not loaded, cannot configure');
  }
}

/**
 * Inject custom CSS
 */
export function injectCSS(css: string, id?: string): void {
  const style = document.createElement('style');
  if (id) {
    style.id = id;
  }
  style.textContent = css;
  document.head.appendChild(style);
  debugLog('CSS injected', id);
}

/**
 * Default FastUI styles
 */
export const FASTUI_DEFAULT_STYLES = `
/* FastUI Default Styles */
[x-cloak] { display: none !important; }

/* HTMX loading indicator */
.htmx-indicator {
  opacity: 0;
  transition: opacity 200ms ease-in;
}
.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator {
  opacity: 1;
}

/* FastUI loading states */
[x-loading] {
  position: relative;
}
[x-loading]::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Chart containers */
[x-chart] {
  min-height: 200px;
}

/* Lazy loading placeholder */
[x-lazy]:not([data-lazy-loaded="true"]) {
  min-height: 100px;
}
`;
