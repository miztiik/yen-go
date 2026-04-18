/**
 * Service Worker for Yen-Go PWA.
 * Implements offline-first strategy with stale-while-revalidate caching.
 * @module sw
 */

/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope;

/**
 * Build-time injected data origin (e.g. 'https://raw.githubusercontent.com').
 * Empty string when VITE_DATA_BASE_URL is not set (local dev).
 */
declare const __DATA_ORIGIN__: string;

/**
 * SyncEvent type for Background Sync API.
 * Not included in standard TypeScript lib.
 */
interface SyncEvent extends ExtendableEvent {
  readonly tag: string;
  readonly lastChance: boolean;
}

const CACHE_NAME = 'yen-go-v2';
const STATIC_CACHE = 'yen-go-static-v2';
const PUZZLE_CACHE = 'yen-go-puzzles-v2';

/**
 * Static assets to pre-cache during installation.
 */
/**
 * Base path matching the Vite `base` config.
 * Must be kept in sync with `vite.config.ts → base`.
 */
const SW_BASE = '/yen-go';

const STATIC_ASSETS = [
  `${SW_BASE}/`,
  `${SW_BASE}/index.html`,
  `${SW_BASE}/offline.html`,
  `${SW_BASE}/manifest.webmanifest`,
  `${SW_BASE}/favicon.ico`,
  `${SW_BASE}/icon-192.png`,
  `${SW_BASE}/icon-512.png`,
];

/**
 * URL patterns for different caching strategies.
 */
const CACHE_PATTERNS = {
  /** Puzzle data files - stale-while-revalidate */
  puzzles: /\/yengo-puzzle-collections\/.*\.json$/,
  /** SGF puzzle files from new collection */
  sgf: /\/yengo-puzzle-collections\/.*\.sgf$/,
  /** SQLite database files - stale-while-revalidate */
  db: /\.db$/,
  /** WASM binary files - cache first (rarely changes) */
  wasm: /\.wasm$/,
  /** Static assets - cache first */
  static: /\.(js|css|woff2?|ttf|eot|svg|png|jpg|jpeg|gif|ico)$/,
  /** HTML pages - network first with fallback */
  html: /\.html$/,
};

/**
 * Install event - pre-cache static assets.
 */
self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(STATIC_CACHE);
      console.log('[SW] Pre-caching static assets');

      // Pre-cache static assets
      await Promise.all(
        STATIC_ASSETS.map(async (url) => {
          try {
            await cache.add(url);
          } catch (error) {
            console.warn(`[SW] Failed to pre-cache ${url}:`, error);
          }
        })
      );

      // Skip waiting to activate immediately
      await self.skipWaiting();
    })()
  );
});

/**
 * Activate event - clean up old caches.
 */
self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    (async () => {
      console.log('[SW] Activating service worker');

      // Clean up old caches
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames
          .filter((name) => {
            // Delete caches that don't match current version
            return name !== STATIC_CACHE && name !== PUZZLE_CACHE && name !== CACHE_NAME;
          })
          .map((name) => {
            console.log(`[SW] Deleting old cache: ${name}`);
            return caches.delete(name);
          })
      );

      // Take control of all clients immediately
      await self.clients.claim();
    })()
  );
});

/**
 * Allowed origins for fetch handling: app origin + optional external data origin.
 */
const ALLOWED_ORIGINS = new Set<string>([location.origin]);
if (__DATA_ORIGIN__) {
  ALLOWED_ORIGINS.add(__DATA_ORIGIN__);
}

/**
 * Check if a URL is a puzzle data request (DB, SGF, puzzle JSON).
 */
function isPuzzleDataRequest(url: URL): boolean {
  return (
    CACHE_PATTERNS.puzzles.test(url.pathname) ||
    CACHE_PATTERNS.sgf.test(url.pathname) ||
    CACHE_PATTERNS.db.test(url.pathname)
  );
}

/**
 * Fetch event - handle requests with appropriate caching strategy.
 */
self.addEventListener('fetch', (event: FetchEvent) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle requests from allowed origins
  if (!ALLOWED_ORIGINS.has(url.origin)) {
    return;
  }

  // For cross-origin data requests, use stale-while-revalidate
  if (url.origin !== location.origin) {
    if (isPuzzleDataRequest(url)) {
      event.respondWith(staleWhileRevalidate(request, PUZZLE_CACHE));
    }
    return;
  }

  // Same-origin: determine caching strategy based on request URL
  if (isPuzzleDataRequest(url)) {
    // Stale-while-revalidate for puzzle data (JSON indexes, SGF, DB files)
    event.respondWith(staleWhileRevalidate(request, PUZZLE_CACHE));
  } else if (CACHE_PATTERNS.wasm.test(url.pathname)) {
    // Cache first for WASM binaries (rarely change)
    event.respondWith(cacheFirst(request, STATIC_CACHE));
  } else if (CACHE_PATTERNS.static.test(url.pathname)) {
    // Cache first for static assets
    event.respondWith(cacheFirst(request, STATIC_CACHE));
  } else if (request.mode === 'navigate' || CACHE_PATTERNS.html.test(url.pathname)) {
    // Network first with offline fallback for navigation
    event.respondWith(networkFirstWithOfflineFallback(request));
  } else {
    // Default: network first
    event.respondWith(networkFirst(request, CACHE_NAME));
  }
});

/**
 * Stale-while-revalidate caching strategy.
 * Returns cached response immediately, then updates cache in background.
 *
 * @param request - Fetch request
 * @param cacheName - Cache to use
 * @returns Response
 */
async function staleWhileRevalidate(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  // Start network fetch in background
  const networkResponsePromise = fetch(request)
    .then(async (response) => {
      if (response.ok) {
        // Update cache with fresh response
        await cache.put(request, response.clone());
        console.log(`[SW] Updated cache: ${request.url}`);
      }
      return response;
    })
    .catch((error) => {
      console.warn(`[SW] Network request failed: ${request.url}`, error);
      return null;
    });

  // Return cached response immediately if available
  if (cachedResponse) {
    console.log(`[SW] Returning cached (stale): ${request.url}`);
    return cachedResponse;
  }

  // Wait for network if no cached response
  const networkResponse = await networkResponsePromise;
  if (networkResponse) {
    return networkResponse;
  }

  // Return error response if both fail
  return new Response('Network error', {
    status: 503,
    statusText: 'Service Unavailable',
  });
}

/**
 * Cache-first caching strategy.
 * Returns cached response if available, otherwise fetches from network.
 *
 * @param request - Fetch request
 * @param cacheName - Cache to use
 * @returns Response
 */
async function cacheFirst(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    console.log(`[SW] Cache hit: ${request.url}`);
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      await cache.put(request, networkResponse.clone());
      console.log(`[SW] Cached: ${request.url}`);
    }
    return networkResponse;
  } catch (error) {
    console.warn(`[SW] Network error for: ${request.url}`, error);
    return new Response('Network error', {
      status: 503,
      statusText: 'Service Unavailable',
    });
  }
}

/**
 * Network-first caching strategy.
 * Tries network first, falls back to cache on failure.
 *
 * @param request - Fetch request
 * @param cacheName - Cache to use
 * @returns Response
 */
async function networkFirst(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      await cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.warn(`[SW] Network failed, checking cache: ${request.url}`);
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    return new Response('Network error', {
      status: 503,
      statusText: 'Service Unavailable',
    });
  }
}

/**
 * Network-first with offline fallback for navigation requests.
 *
 * @param request - Navigation request
 * @returns Response
 */
async function networkFirstWithOfflineFallback(request: Request): Promise<Response> {
  try {
    const networkResponse = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch {
    // Try to return cached version
    const cache = await caches.open(CACHE_NAME);
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline page
    const staticCache = await caches.open(STATIC_CACHE);
    const offlinePage = await staticCache.match(`${SW_BASE}/offline.html`);
    if (offlinePage) {
      return offlinePage;
    }

    // Last resort fallback
    return new Response(
      '<html><body><h1>Offline</h1><p>Please check your internet connection.</p></body></html>',
      {
        status: 503,
        headers: { 'Content-Type': 'text/html' },
      }
    );
  }
}

/**
 * Message event - handle messages from main thread.
 */
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  const { type, payload } = (event.data || {}) as { type?: string; payload?: { urls?: string[] } };

  switch (type) {
    case 'SKIP_WAITING':
      void self.skipWaiting();
      break;

    case 'CACHE_PUZZLES':
      // Pre-cache specific puzzle files
      if (payload?.urls && Array.isArray(payload.urls)) {
        const urlsToCache = payload.urls;
        event.waitUntil(
          (async () => {
            const cache = await caches.open(PUZZLE_CACHE);
            await Promise.all(
              urlsToCache.map(async (url: string) => {
                try {
                  const response = await fetch(url);
                  if (response.ok) {
                    await cache.put(url, response);
                    console.log(`[SW] Pre-cached puzzle: ${url}`);
                  }
                } catch (error) {
                  console.warn(`[SW] Failed to pre-cache puzzle: ${url}`, error);
                }
              })
            );
          })()
        );
      }
      break;

    case 'CLEAR_CACHE':
      event.waitUntil(
        (async () => {
          const cacheNames = await caches.keys();
          await Promise.all(cacheNames.map((name) => caches.delete(name)));
          console.log('[SW] All caches cleared');
        })()
      );
      break;

    default:
      console.log(`[SW] Unknown message type: ${type}`);
  }
});

/**
 * Background sync event - sync data when online.
 * Note: 'sync' event is part of Background Sync API, not yet in TS lib.
 */
self.addEventListener('sync', ((event: SyncEvent) => {
  if (event.tag === 'sync-progress') {
    event.waitUntil(
      Promise.resolve().then(() => {
        console.log('[SW] Syncing progress data');
      })
    );
  }
}) as EventListener);

// Export empty object for module compatibility
export {};
