// Shop Notes storage page: offline copy. After the first visit the page loads from this cache when the site cannot be
// reached (offline, GitHub Pages down). Online, the newest page is fetched first and the cache is refreshed.
// Only this folder's page is handled; notes themselves live in the page's localStorage, never in this cache.
'use strict';
var CACHE = 'shop-notes-page-v2';
var PAGE = new URL('./index.html', self.location).href;
var ROOT = new URL('./', self.location).href;
self.addEventListener('install', function (e) {
    e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll([ROOT, PAGE]); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
    e.waitUntil(caches.keys().then(function (ks) {
        return Promise.all(ks.filter(function (k) { return k.indexOf('shop-notes-page-') === 0 && k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); }));
});
function isPage(url) { var u = new URL(url); u.search = ''; u.hash = ''; return u.href === ROOT || u.href === PAGE; }
self.addEventListener('fetch', function (e) {
    var req = e.request;
    if (req.method !== 'GET' || !isPage(req.url)) return;
    e.respondWith(new Promise(function (resolve) {
        var done = false;
        function fromCache() {
            if (done) return; done = true;
            caches.match(PAGE).then(function (r) { return r || caches.match(ROOT); }).then(function (r) { resolve(r || Response.error()); });
        }
        var timer = setTimeout(fromCache, 4000);   // a host that hangs counts as offline
        fetch(req).then(function (r) {
            clearTimeout(timer);
            if (r && r.ok) {
                var copy = r.clone();
                caches.open(CACHE).then(function (c) { return c.put(PAGE, copy); });
                if (!done) { done = true; resolve(r); }
            } else fromCache();
        }).catch(function () { clearTimeout(timer); fromCache(); });
    }));
});
