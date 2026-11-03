// Offline cache: app shell first, stickers and sounds as they are used.
const V = 'stickersounds-v3';
const SHELL = ['./', 'index.html', 'app.css', 'app.js', 'stickers.json', 'manifest.webmanifest', 'icons/icon-192.png', 'fonts/barlow-xbi.woff2', 'fonts/barlow-sbi.woff2', 'fonts/sharetechmono.woff2'];
self.addEventListener('install', e => e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || !e.request.url.startsWith(self.location.origin)) return;
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
    if (r.ok) { const copy = r.clone(); caches.open(V).then(c => c.put(e.request, copy)); }
    return r;
  })));
});
