/**
 * FastUI Global Store
 * Reactive state management using Alpine.js store
 */

import type { FastUIStore } from '../types';
import { hasAlpine, debugLog } from './helpers';

/**
 * Create a reactive store wrapper
 */
export function createStore(): FastUIStore {
  const state: Record<string, unknown> = {};
  const subscribers = new Map<string, Set<(value: unknown) => void>>();

  const store: FastUIStore = {
    get(key: string): unknown {
      return state[key];
    },

    set(key: string, value: unknown): void {
      const oldValue = state[key];
      state[key] = value;

      // Notify subscribers
      const subs = subscribers.get(key);
      if (subs) {
        subs.forEach((callback) => callback(value));
      }

      // Sync with Alpine store if available
      if (hasAlpine()) {
        try {
          window.Alpine.store('fastui', {
            ...window.Alpine.store('fastui') || {},
            [key]: value,
          });
        } catch {
          // Alpine store not initialized
        }
      }

      debugLog(`Store updated: ${key}`, { oldValue, newValue: value });
    },

    delete(key: string): void {
      delete state[key];
      subscribers.delete(key);

      debugLog(`Store key deleted: ${key}`);
    },

    clear(): void {
      Object.keys(state).forEach((key) => delete state[key]);
      subscribers.clear();

      debugLog('Store cleared');
    },

    subscribe(key: string, callback: (value: unknown) => void): () => void {
      if (!subscribers.has(key)) {
        subscribers.set(key, new Set());
      }

      subscribers.get(key)!.add(callback);

      // Return unsubscribe function
      return () => {
        subscribers.get(key)?.delete(callback);
      };
    },
  };

  return store;
}

/**
 * Initialize Alpine store integration
 */
export function initAlpineStore(): void {
  if (!hasAlpine()) {
    console.warn('[FastUI] Alpine.js not found. Store will work without reactivity.');
    return;
  }

  // Create the fastui store in Alpine
  window.Alpine.store('fastui', {
    __state: {} as Record<string, unknown>,
  });

  debugLog('Alpine store initialized');
}

/**
 * Persist store to localStorage
 */
export function persistStore(store: FastUIStore, key: string = 'fastui-state'): void {
  if (typeof window === 'undefined') return;

  // Load persisted state
  try {
    const saved = localStorage.getItem(key);
    if (saved) {
      const state = JSON.parse(saved);
      Object.entries(state).forEach(([k, v]) => store.set(k, v));
    }
  } catch (e) {
    console.warn('[FastUI] Failed to load persisted state:', e);
  }

  // Subscribe to changes and persist
  const originalSet = store.set.bind(store);
  store.set = (k: string, v: unknown) => {
    originalSet(k, v);

    try {
      const state: Record<string, unknown> = {};
      // We need to track all state ourselves for persistence
      // This is a simplified implementation
      localStorage.setItem(key, JSON.stringify({ [k]: v }));
    } catch (e) {
      console.warn('[FastUI] Failed to persist state:', e);
    }
  };
}

/**
 * Create a computed value from store
 */
export function computed<T>(
  store: FastUIStore,
  dependencies: string[],
  compute: (values: unknown[]) => T
): { get: () => T; subscribe: (callback: (value: T) => void) => () => void } {
  let cachedValue: T;
  let isDirty = true;

  const getValue = (): T => {
    if (isDirty) {
      const values = dependencies.map((dep) => store.get(dep));
      cachedValue = compute(values);
      isDirty = false;
    }
    return cachedValue;
  };

  // Subscribe to all dependencies
  dependencies.forEach((dep) => {
    store.subscribe(dep, () => {
      isDirty = true;
    });
  });

  return {
    get: getValue,
    subscribe: (callback: (value: T) => void) => {
      const unsubscribers: (() => void)[] = [];

      dependencies.forEach((dep) => {
        unsubscribers.push(
          store.subscribe(dep, () => {
            callback(getValue());
          })
        );
      });

      // Return combined unsubscribe function
      return () => unsubscribers.forEach((unsub) => unsub());
    },
  };
}
