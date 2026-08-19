/*
 * Service worker for SS Tuitions.
 *
 * Its job is narrow on purpose. A service worker sits in front of every
 * request and outlives any deploy, so an over-eager one serves last week's
 * app to people who cannot clear it. The rules here are:
 *
 *   1. API requests are never touched. They go to a different origin and
 *      carry a signed-in session; a cached response could show one person
 *      another person's data, and a stale fee balance is worse than none.
 *
 *   2. Pages are network-first. The network answer always wins, so a deploy
 *      takes effect immediately. The cache only stands in when the device is
 *      offline, which is the whole reason to have one.
 *
 *   3. Build assets are cache-first, because their filenames contain a
 *      content hash. A given URL's bytes can never change, so serving them
 *      from cache cannot go stale.
 *
 * Chrome also requires a fetch handler before it will offer to install the
 * app, which is the other reason this file exists.
 */

const VERSION = "v1";
const PAGES = `ss-pages-${VERSION}`;
const ASSETS = `ss-assets-${VERSION}`;
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(PAGES)
      .then((cache) => cache.add(OFFLINE_URL))
      // Take over straight away rather than waiting for every tab to close.
      // Without this an update can sit unused for days.
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((n) => n !== PAGES && n !== ASSETS)
            .map((n) => caches.delete(n)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Only GET is cacheable, and only our own origin. Anything else -- the API
  // on Render, a POST, a cross-origin font -- passes straight through.
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Immutable build output: safe to serve from cache, then fill in.
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.open(ASSETS).then(async (cache) => {
        const hit = await cache.match(request);
        if (hit) return hit;
        const response = await fetch(request);
        if (response.ok) cache.put(request, response.clone());
        return response;
      }),
    );
    return;
  }

  // Pages: network wins, cache is the fallback for being offline.
  if (request.mode === "navigate") {
    event.respondWith(
      (async () => {
        try {
          const response = await fetch(request);
          if (response.ok) {
            const cache = await caches.open(PAGES);
            cache.put(request, response.clone());
          }
          return response;
        } catch {
          const cached = await caches.match(request);
          return cached || (await caches.match(OFFLINE_URL));
        }
      })(),
    );
  }
});
