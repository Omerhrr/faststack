/**
 * FastUI HTMX Integration Plugin
 * Auto-reinitializes components after HTMX swaps
 */

import type { FastUIPlugin } from '../types';
import { debugLog, hasHTMX, hasAlpine } from '../utils/helpers';
import { initFlowbiteComponents, cleanupFlowbiteComponents } from '../directives/flow';
import { resizeAllCharts } from '../directives/chart';

/**
 * Create HTMX integration plugin
 */
export function createHTMXPlugin(): FastUIPlugin {
  return {
    name: 'htmx',

    install(): void {
      if (!hasHTMX()) {
        debugLog('HTMX not found, skipping plugin installation');
        return;
      }

      // Register event listeners
      setupEventListeners();

      debugLog('HTMX plugin installed');
    },

    uninstall(): void {
      removeEventListeners();
      debugLog('HTMX plugin uninstalled');
    },
  };
}

/**
 * Event listener references for cleanup
 */
const eventListeners: Array<{ event: string; handler: EventListener }> = [];

/**
 * Setup HTMX event listeners
 */
function setupEventListeners(): void {
  // After HTMX swaps content
  const afterSettleHandler = (event: Event) => {
    const customEvent = event as CustomEvent<{ target: HTMLElement }>;
    const target = customEvent.detail?.target || (event.target as HTMLElement);

    debugLog('HTMX afterSettle, reinitializing', target);

    // Reinitialize Alpine in swapped content
    if (hasAlpine()) {
      reinitAlpine(target);
    }

    // Reinitialize Flowbite components
    initFlowbiteComponents(target);

    // Resize charts
    resizeAllCharts();

    // Dispatch FastUI event
    window.dispatchEvent(
      new CustomEvent('fastui:reinit', {
        detail: { target, source: 'htmx:afterSettle' },
      })
    );
  };

  // Before HTMX swaps - save state
  const beforeSwapHandler = (event: Event) => {
    const customEvent = event as CustomEvent<{ target: HTMLElement }>;
    const target = customEvent.detail?.target || (event.target as HTMLElement);

    debugLog('HTMX beforeSwap, saving state', target);

    // Save Alpine state
    saveAlpineState(target);

    // Cleanup old Flowbite instances
    cleanupFlowbiteComponents(target);
  };

  // After HTMX request - handle errors
  const afterRequestHandler = (event: Event) => {
    const customEvent = event as CustomEvent<{ xhr: XMLHttpRequest; target: HTMLElement }>;
    const xhr = customEvent.detail?.xhr;

    if (xhr?.status >= 400) {
      debugLog('HTMX request error', xhr.status);
      window.dispatchEvent(
        new CustomEvent('fastui:error', {
          detail: {
            status: xhr.status,
            response: xhr.responseText,
            target: customEvent.detail?.target,
          },
        })
      );
    }
  };

  // Register listeners
  document.addEventListener('htmx:afterSettle', afterSettleHandler);
  document.addEventListener('htmx:beforeSwap', beforeSwapHandler);
  document.addEventListener('htmx:afterRequest', afterRequestHandler);

  // Store for cleanup
  eventListeners.push(
    { event: 'htmx:afterSettle', handler: afterSettleHandler },
    { event: 'htmx:beforeSwap', handler: beforeSwapHandler },
    { event: 'htmx:afterRequest', handler: afterRequestHandler }
  );
}

/**
 * Remove HTMX event listeners
 */
function removeEventListeners(): void {
  eventListeners.forEach(({ event, handler }) => {
    document.removeEventListener(event, handler);
  });
  eventListeners.length = 0;
}

/**
 * Reinitialize Alpine.js in an element
 */
function reinitAlpine(el: HTMLElement): void {
  if (!hasAlpine()) return;

  try {
    // Find all Alpine elements within the swapped content
    const alpineElements = el.querySelectorAll('[x-data]');

    alpineElements.forEach((element) => {
      // Force Alpine to reinitialize this element
      const htmlEl = element as HTMLElement;

      // Check if already initialized
      if (!(htmlEl as unknown as { __x?: unknown }).__x) {
        window.Alpine.initTree(htmlEl);
      }
    });

    // Also check the element itself
    if (el.hasAttribute('x-data') && !(el as unknown as { __x?: unknown }).__x) {
      window.Alpine.initTree(el);
    }

    debugLog('Alpine reinitialized');
  } catch (e) {
    console.warn('[FastUI] Failed to reinitialize Alpine:', e);
  }
}

/**
 * Save Alpine state before swap
 */
function saveAlpineState(el: HTMLElement): void {
  if (!hasAlpine()) return;

  const alpineEl = el as unknown as { __x?: { $data: Record<string, unknown> } };
  if (alpineEl.__x?.$data) {
    // Get element identifier
    const elId = el.id || el.getAttribute('hx-target') || el.tagName;

    // Filter out Alpine internals
    const state: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(alpineEl.__x.$data)) {
      if (!key.startsWith('$') && typeof value !== 'function') {
        state[key] = value;
      }
    }

    // Save to session storage for potential restoration
    if (Object.keys(state).length > 0) {
      sessionStorage.setItem(`fastui-state:${elId}`, JSON.stringify(state));
      debugLog('Alpine state saved', elId);
    }
  }
}

/**
 * Restore Alpine state after swap
 */
export function restoreAlpineState(el: HTMLElement): void {
  if (!hasAlpine()) return;

  const elId = el.id || el.getAttribute('hx-target') || el.tagName;
  const savedState = sessionStorage.getItem(`fastui-state:${elId}`);

  if (savedState) {
    try {
      const state = JSON.parse(savedState);
      const alpineEl = el as unknown as { __x?: { $data: Record<string, unknown> } };

      // Wait for Alpine to initialize
      setTimeout(() => {
        if (alpineEl.__x?.$data) {
          Object.assign(alpineEl.__x.$data, state);
          debugLog('Alpine state restored', elId);
        }
      }, 0);
    } catch (e) {
      debugLog('Failed to restore Alpine state', e);
    }
  }
}

/**
 * Configure HTMX defaults for FastUI
 */
export function configureHTMXDefaults(): void {
  if (!hasHTMX()) return;

  // Set default swap style
  window.htmx.config.defaultSwapStyle = 'innerHTML';

  // Enable indicator
  window.htmx.config.includeIndicatorStyles = true;

  // Set timeout
  window.htmx.config.timeout = 30000;

  debugLog('HTMX defaults configured');
}
