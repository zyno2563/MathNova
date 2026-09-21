/**
 * MathNova service worker.
 *
 * Its job is narrow: make the app installable and fail gracefully
 * offline. It is deliberately *network-first* for everything it
 * caches, so a deploy is never hidden behind a stale copy — the cache
 * is only ever a fallback for when the network is gone.
 *
 * The API is never cached. Every calculation must come from the live
 * engines; a cached result would be a wrong answer waiting to happen.
 */

// Bump when the offline shell changes, so old caches are dropped.
const CACHE = 'mathnova-v1';

const OFFLINE_URL = '/offline.html';

// Enough to render the offline page with its styling and icon.
const PRECACHE = [
  OFFLINE_URL,
  '/css/styles.css',
  '/css/pages.css',
  '/icons/icon-192.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Only same-origin GETs. Everything else — POSTs to the API, the
  // KaTeX CDN — goes straight to the network, untouched.
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // Never serve a calculation or a health check from cache.
  if (url.pathname.startsWith('/api/')) return;

  event.respondWith(networkFirst(request));
});

async function networkFirst(request) {
  try {
    const response = await fetch(request);

    // Keep a copy of good responses as the offline fallback.
    if (response.ok && response.type === 'basic') {
      const copy = response.clone();
      caches.open(CACHE).then((cache) => cache.put(request, copy));
    }

    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;

    if (request.mode === 'navigate') {
      const offline = await caches.match(OFFLINE_URL);
      if (offline) return offline;
    }

    throw error;
  }
}
