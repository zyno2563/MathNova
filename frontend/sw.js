/**
 * MathNova service worker.
 *
 * Its job is narrow: make the app installable and fail gracefully
 * offline. Prefer the network, but show a previously visited page after
 * a short wait while a sleeping server wakes. Refresh the cached copy
 * in the background. Calculations still require the live server.
 *
 * The API is never cached. Every calculation must come from the live
 * engines; a cached result would be a wrong answer waiting to happen.
 */

// Bump when the offline shell changes, so old caches are dropped.
const CACHE = 'mathnova-v2-bounded-startup';

const OFFLINE_URL = '/offline.html';

// Enough to render the offline page with its styling and icon.
const PRECACHE = [
  '/',
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

  // Only public static files; avoid saving arbitrary query strings (which
  // can include a user's matrix input) or unbounded unknown routes.
  const page = /^\/(?:solver|learn|assistant|settings|about|contact|disclaimer|terms|privacy)\/$/.test(url.pathname);
  const asset = /^\/(?:js|css|icons)\//.test(url.pathname);
  if (!page && !asset && !['/', OFFLINE_URL, '/manifest.json'].includes(url.pathname)) return;
  event.respondWith(networkFirst(request, event));
});

async function networkFirst(request, event) {
  const url = new URL(request.url);
  const key = url.origin + url.pathname;
  const cache = await caches.open(CACHE);
  const fresh = fetch(request).then(async response => {
    // Render's temporary loading page can return 200 too. Only cache
    // responses actually served by MathNova, never that interstitial.
    if (response.ok && response.type === 'basic' && response.headers.get('X-MathNova-App') === '1') {
      await cache.put(key, response.clone());
    }
    return response;
  });
  event.waitUntil(fresh.then(() => {}, () => {}));
  const cached = await cache.match(key);
  let timer;
  try {
    if (cached) {
      return await Promise.race([
        fresh.then(response => response.ok && response.headers.get('X-MathNova-App') === '1' ? response : cached).catch(() => cached),
        new Promise(resolve => { timer = setTimeout(() => resolve(cached), 2000); })
      ]);
    }
    return await fresh;
  } catch (error) {
    if (request.mode === 'navigate') {
      const offline = await cache.match(OFFLINE_URL);
      if (offline) return offline;
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
