/* GEO-SENTINEL field-reporting service worker (offline queue support only).
   Caches the app shell for the report flow; dashboard/map tiles stay online.
   Critical read-only data (zones, alerts, emergency tasks) is cached on
   successful fetch so field users keep last-known-good context offline —
   labeled STALE by age in the UI, never presented as live.
   Update policy (fixed 2026-09-18 after stale-shell blank screens): the app
   SHELL (/, /index.html) is NETWORK-FIRST so redeploys can never strand a
   client on an HTML file pointing at deleted hashed bundles; old caches are
   purged on activate. Hashed /assets/* bundles stay cache-first (immutable).
   Only cache same-origin GETs — never third-party tiles or API POSTs. */
const CACHE = "gs-field-v3";
const SHELL = ["/", "/index.html", "/manifest.webmanifest"];
const CRITICAL_GET = ["/api/zones", "/api/alerts", "/api/emergency/tasks",
                      "/api/exposure/villages", "/api/data-status"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()));
});
function netFirst(req, fallbackKey) {
  return fetch(req).then((res) => {
    const copy = res.clone();
    caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
    return res;
  }).catch(() => caches.match(req).then((hit) => hit || caches.match(fallbackKey || "/index.html")));
}
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return; // queued POSTs handled by IndexedDB in app
  if (url.origin !== self.location.origin) return; // never cache third-party tiles
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/media/")) {
    const critical = CRITICAL_GET.some((p) => url.pathname === p || url.pathname.startsWith(p + "?") || url.pathname === p);
    if (critical && url.pathname.startsWith("/api/")) {
      e.respondWith(netFirst(e.request, "/index.html"));
      return;
    }
    e.respondWith(fetch(e.request).catch(() => caches.match("/index.html")));
    return;
  }
  // App shell navigations: NETWORK-FIRST (deploy-safe).
  if (e.request.mode === "navigate" || url.pathname === "/" || url.pathname === "/index.html") {
    e.respondWith(netFirst(e.request, "/index.html"));
    return;
  }
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
    const copy = res.clone();
    caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
    return res;
  }).catch(() => caches.match("/index.html"))));
});
