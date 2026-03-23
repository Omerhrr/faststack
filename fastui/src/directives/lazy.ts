/**
 * FastUI x-lazy Directive
 * Alpine.js directive for lazy loading content
 */

import type { LazyLoadOptions } from '../types';
import { debugLog, safeParseJSON } from '../utils/helpers';

/**
 * Lazy load observers registry
 */
const observers = new Map<string, IntersectionObserver>();

/**
 * Default lazy load options
 */
const defaultOptions: LazyLoadOptions = {
  rootMargin: '100px',
  threshold: 0.1,
  triggerOnce: true,
};

/**
 * Create x-lazy Alpine directive
 */
export function createLazyDirective() {
  return {
    name: 'lazy',

    callback(el: HTMLElement, value: string): void {
      // Parse options
      let options: LazyLoadOptions = { ...defaultOptions };

      if (value) {
        const parsedOptions = safeParseJSON(value, {});
        options = { ...options, ...parsedOptions };
      }

      // Also check for data-lazy-options attribute
      const optionsAttr = el.dataset.lazyOptions;
      if (optionsAttr) {
        const parsedOptions = safeParseJSON(optionsAttr, {});
        options = { ...options, ...parsedOptions };
      }

      // Mark element as lazy
      el.dataset.lazyLoaded = 'false';

      // Create observer
      const observerId = `lazy-${Date.now()}`;
      const observer = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const target = entry.target as HTMLElement;

              // Mark as loaded
              target.dataset.lazyLoaded = 'true';

              // Load content
              loadContent(target);

              // Dispatch event
              target.dispatchEvent(
                new CustomEvent('fastui:lazy:loaded', {
                  bubbles: true,
                  detail: { element: target },
                })
              );

              // Callback
              options.onVisible?.(target);

              // Unobserve if triggerOnce
              if (options.triggerOnce) {
                obs.unobserve(target);
              }
            } else {
              options.onHidden?.(entry.target as HTMLElement);
            }
          });
        },
        {
          rootMargin: options.rootMargin,
          threshold: options.threshold,
        }
      );

      observers.set(observerId, observer);
      observer.observe(el);

      debugLog('Lazy observer created', el);
    },
  };
}

/**
 * Load lazy content
 */
function loadContent(el: HTMLElement): void {
  // Check for data-lazy-src (load HTML from URL)
  const src = el.dataset.lazySrc;
  if (src) {
    fetch(src)
      .then((response) => response.text())
      .then((html) => {
        el.innerHTML = html;
        el.dispatchEvent(
          new CustomEvent('fastui:lazy:contentLoaded', {
            bubbles: true,
            detail: { html },
          })
        );
      })
      .catch((e) => {
        console.error('[FastUI] Failed to load lazy content:', e);
      });
    return;
  }

  // Check for data-lazy-html (load from attribute)
  const lazyHtml = el.dataset.lazyHtml;
  if (lazyHtml) {
    el.innerHTML = lazyHtml;
    return;
  }

  // Check for data-lazy-template (load from template)
  const templateId = el.dataset.lazyTemplate;
  if (templateId) {
    const template = document.getElementById(templateId);
    if (template?.innerHTML) {
      el.innerHTML = template.innerHTML;
    }
    return;
  }

  // Check for data-lazy-component (load web component)
  const componentName = el.dataset.lazyComponent;
  if (componentName) {
    // Load component script if not already loaded
    const scriptUrl = el.dataset.lazyScript;
    if (scriptUrl) {
      loadScript(scriptUrl).then(() => {
        el.innerHTML = `<${componentName}></${componentName}>`;
      });
    } else {
      el.innerHTML = `<${componentName}></${componentName}>`;
    }
    return;
  }
}

/**
 * Load script dynamically
 */
function loadScript(src: string): Promise<void> {
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
 * Create x-init-fragment directive for cached fragment initialization
 */
export function createInitFragmentDirective() {
  return {
    name: 'init-fragment',

    callback(el: HTMLElement, value: string): void {
      // Get cache key
      const cacheKey = value || el.dataset.fragmentKey;

      if (!cacheKey) {
        debugLog('No cache key provided for x-init-fragment');
        return;
      }

      // Check if we have cached state
      const cachedState = sessionStorage.getItem(`fastui-fragment:${cacheKey}`);
      if (cachedState) {
        try {
          const state = JSON.parse(cachedState);

          // Restore state to Alpine data
          const alpineEl = el as unknown as { __x?: { $data: Record<string, unknown> } };
          if (alpineEl.__x?.$data) {
            Object.assign(alpineEl.__x.$data, state);
          }

          debugLog('Fragment state restored', cacheKey);
        } catch (e) {
          debugLog('Failed to restore fragment state', e);
        }
      }

      // Save state before HTMX swap
      document.addEventListener('htmx:beforeSwap', () => {
        const alpineEl = el as unknown as { __x?: { $data: Record<string, unknown> } };
        if (alpineEl.__x?.$data) {
          // Filter out Alpine internals
          const state: Record<string, unknown> = {};
          for (const [key, value] of Object.entries(alpineEl.__x.$data)) {
            if (!key.startsWith('$') && typeof value !== 'function') {
              state[key] = value;
            }
          }

          sessionStorage.setItem(`fastui-fragment:${cacheKey}`, JSON.stringify(state));
        }
      });
    },
  };
}

/**
 * Cleanup lazy observers
 */
export function cleanupLazyObservers(): void {
  observers.forEach((observer) => observer.disconnect());
  observers.clear();
}

/**
 * Check if element is lazy loaded
 */
export function isLazyLoaded(el: HTMLElement): boolean {
  return el.dataset.lazyLoaded === 'true';
}

/**
 * Force load lazy element
 */
export function forceLazyLoad(el: HTMLElement): void {
  el.dataset.lazyLoaded = 'true';
  loadContent(el);
}
