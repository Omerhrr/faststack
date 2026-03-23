/**
 * FastUI Utility Functions
 */

import type { FastUIConfig, LazyLoadOptions } from '../types';

/**
 * Default FastUI configuration
 */
export const defaultConfig: FastUIConfig = {
  debug: false,
  cacheEnabled: true,
  cacheTTL: 5 * 60 * 1000, // 5 minutes
  lazyLoadECharts: true,
  lazyLoadFlowbite: true,
  autoReinit: true,
  tailwindCDN: 'https://cdn.tailwindcss.com',
};

/**
 * Merge configuration with defaults
 */
export function mergeConfig(userConfig?: Partial<FastUIConfig>): FastUIConfig {
  return { ...defaultConfig, ...userConfig };
}

/**
 * Check if code is running in browser
 */
export function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

/**
 * Check if Alpine.js is available
 */
export function hasAlpine(): boolean {
  return isBrowser() && typeof window.Alpine !== 'undefined';
}

/**
 * Check if HTMX is available
 */
export function hasHTMX(): boolean {
  return isBrowser() && typeof window.htmx !== 'undefined';
}

/**
 * Check if ECharts is available
 */
export function hasECharts(): boolean {
  return isBrowser() && typeof window.echarts !== 'undefined';
}

/**
 * Check if Flowbite is available
 */
export function hasFlowbite(): boolean {
  return isBrowser() && typeof (window as unknown as { flowbite?: unknown }).flowbite !== 'undefined';
}

/**
 * Generate unique ID
 */
let idCounter = 0;
export function generateId(prefix = 'fastui'): string {
  return `${prefix}-${Date.now()}-${++idCounter}`;
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Throttle function
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Deep merge objects
 */
export function deepMerge<T extends Record<string, unknown>>(
  target: T,
  ...sources: Partial<T>[]
): T {
  if (!sources.length) return target;
  const source = sources.shift();

  if (isObject(target) && isObject(source)) {
    for (const key in source) {
      if (isObject(source[key])) {
        if (!target[key]) Object.assign(target, { [key]: {} });
        deepMerge(target[key] as Record<string, unknown>, source[key] as Record<string, unknown>);
      } else {
        Object.assign(target, { [key]: source[key] });
      }
    }
  }

  return deepMerge(target, ...sources);
}

/**
 * Check if value is a plain object
 */
export function isObject(item: unknown): item is Record<string, unknown> {
  return item !== null && typeof item === 'object' && !Array.isArray(item);
}

/**
 * Parse JSON safely
 */
export function safeParseJSON<T>(json: string, fallback: T): T {
  try {
    return JSON.parse(json) as T;
  } catch {
    return fallback;
  }
}

/**
 * Create intersection observer for lazy loading
 */
export function createLazyObserver(
  options: LazyLoadOptions = {}
): IntersectionObserver {
  const { rootMargin = '100px', threshold = 0.1, triggerOnce = true } = options;

  return new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          options.onVisible?.(entry.target as HTMLElement);
          if (triggerOnce) {
            observer.unobserve(entry.target);
          }
        } else if (!triggerOnce) {
          options.onHidden?.(entry.target as HTMLElement);
        }
      });
    },
    { rootMargin, threshold }
  );
}

/**
 * Load script dynamically
 */
export function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.head.appendChild(script);
  });
}

/**
 * Load CSS dynamically
 */
export function loadCSS(href: string): Promise<void> {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    const existing = document.querySelector(`link[href="${href}"]`);
    if (existing) {
      resolve();
      return;
    }

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.onload = () => resolve();
    link.onerror = () => reject(new Error(`Failed to load CSS: ${href}`));
    document.head.appendChild(link);
  });
}

/**
 * Dispatch custom event
 */
export function dispatchEvent(name: string, detail?: unknown): void {
  window.dispatchEvent(new CustomEvent(`fastui:${name}`, { detail }));
}

/**
 * Log debug messages
 */
export function debugLog(message: string, ...args: unknown[]): void {
  if (typeof __DEV__ !== 'undefined' && __DEV__) {
    console.log(`%c[FastUI]%c ${message}`, 'color: #3b82f6; font-weight: bold', '', ...args);
  }
}

/**
 * Query selector shorthand with error handling
 */
export function $<T extends HTMLElement>(selector: string, context: HTMLElement | Document = document): T | null {
  return context.querySelector<T>(selector);
}

/**
 * Query selector all shorthand
 */
export function $$<T extends HTMLElement>(selector: string, context: HTMLElement | Document = document): NodeListOf<T> {
  return context.querySelectorAll<T>(selector);
}

/**
 * Check if element is visible in viewport
 */
export function isInViewport(el: HTMLElement): boolean {
  const rect = el.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

/**
 * Auto-resize element to fit content
 */
export function autoResize(el: HTMLElement): void {
  el.style.height = 'auto';
  el.style.height = `${el.scrollHeight}px`;
}

/**
 * Get data attributes from element
 */
export function getDataAttributes(el: HTMLElement): Record<string, string> {
  const data: Record<string, string> = {};
  for (const attr of el.attributes) {
    if (attr.name.startsWith('data-')) {
      data[attr.name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = attr.value;
    }
  }
  return data;
}
