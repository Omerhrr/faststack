/**
 * FastUI Fragment Cache
 * Caches HTMX fragments for improved performance
 */

import type { FastUICache, CachedFragment } from '../types';

/**
 * Create a new fragment cache
 */
export function createFragmentCache(defaultTTL: number = 5 * 60 * 1000): FastUICache {
  const cache = new Map<string, CachedFragment>();

  /**
   * Clean up expired entries
   */
  function cleanup(): void {
    const now = Date.now();
    for (const [key, fragment] of cache.entries()) {
      if (now - fragment.timestamp > fragment.ttl) {
        cache.delete(key);
      }
    }
  }

  // Run cleanup every minute
  if (typeof window !== 'undefined') {
    setInterval(cleanup, 60 * 1000);
  }

  return {
    get(key: string): CachedFragment | null {
      const fragment = cache.get(key);
      if (!fragment) return null;

      // Check if expired
      if (Date.now() - fragment.timestamp > fragment.ttl) {
        cache.delete(key);
        return null;
      }

      return fragment;
    },

    set(key: string, fragment: CachedFragment): void {
      cache.set(key, {
        ...fragment,
        timestamp: fragment.timestamp || Date.now(),
        ttl: fragment.ttl || defaultTTL,
      });
    },

    delete(key: string): void {
      cache.delete(key);
    },

    clear(): void {
      cache.clear();
    },

    has(key: string): boolean {
      const fragment = cache.get(key);
      if (!fragment) return false;

      // Check if expired
      if (Date.now() - fragment.timestamp > fragment.ttl) {
        cache.delete(key);
        return false;
      }

      return true;
    },
  };
}

/**
 * Generate cache key from URL and parameters
 */
export function generateCacheKey(url: string, params?: Record<string, string>): string {
  const urlObj = new URL(url, window.location.origin);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      urlObj.searchParams.set(key, value);
    });
  }

  return urlObj.toString();
}

/**
 * Cache middleware for HTMX requests
 */
export function setupCacheMiddleware(cache: FastUICache): void {
  if (typeof window === 'undefined' || !window.htmx) return;

  // Cache fragments before swap
  document.addEventListener('htmx:beforeSwap', (event) => {
    const customEvent = event as CustomEvent;
    const target = customEvent.detail?.target as HTMLElement;
    const xhr = customEvent.detail?.xhr;

    if (target && xhr) {
      const cacheKey = xhr.responseURL || generateCacheKey(xhr.responseURL);
      const cacheControl = xhr.getResponseHeader('Cache-Control');
      
      // Check if response should be cached
      if (cacheControl?.includes('no-store') || cacheControl?.includes('no-cache')) {
        return;
      }

      // Extract TTL from Cache-Control max-age
      const maxAgeMatch = cacheControl?.match(/max-age=(\d+)/);
      const ttl = maxAgeMatch ? parseInt(maxAgeMatch[1], 10) * 1000 : undefined;

      cache.set(cacheKey, {
        html: customEvent.detail?.serverResponse || '',
        timestamp: Date.now(),
        ttl: ttl || 5 * 60 * 1000,
      });
    }
  });
}
