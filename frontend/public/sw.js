/* Service worker (P4). File ngoài (hợp CSP script-src/worker-src 'self'), Caddy gửi Cache-Control: no-cache.
   - Cache "app shell" (index.html, assets đã build, theme-init.js, manifest, icon); assets: stale-while-revalidate.
   - Điều hướng khi offline ⇒ index.html đã cache.
   - KHÔNG BAO GIỜ cache /api/* (dữ liệu sức khỏe) — xem shouldCache(); test: src/pwa.test.ts.
   - VERSION được thay khi build (vite.config.ts) ⇒ mỗi bản build một cache, cache cũ bị xóa khi activate. */
const VERSION = "hnag-__SW_VERSION__";
const SHELL = ["/", "/index.html", "/theme-init.js", "/manifest.webmanifest", "/icons/icon-192.png",
  "/icons/icon-512.png", "/icons/maskable-512.png"];

function shouldCache(url, origin) {
  const u = new URL(url, origin);
  if (u.origin !== origin) return false; // không cache tài nguyên bên ngoài
  if (u.pathname === "/api" || u.pathname.startsWith("/api/")) return false; // dữ liệu sức khỏe: chỉ mạng
  if (u.pathname === "/sw.js") return false;
  return true;
}

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k.startsWith("hnag-") && k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || !shouldCache(req.url, self.location.origin)) return; // /api: trình duyệt tự gọi mạng
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match("/index.html")));
    return;
  }
  e.respondWith(caches.open(VERSION).then(async (cache) => {
    const hit = await cache.match(req);
    const net = fetch(req).then((res) => {
      if (res.ok && res.type === "basic") cache.put(req, res.clone());
      return res;
    }).catch(() => hit);
    return hit || net;
  }));
});
