/* 도쿄 플랜 — 오프라인 캐시 */
var VERSION = "26.09.23-0009";
var CACHE = "tp-v" + VERSION;
var CORE = ["./", "./index.html", "./data.json", "./manifest.webmanifest",
            "./apple-touch-icon.png", "./icon-192.png", "./icon-512.png"];

function fresh(u){ return new Request(u, { cache: "reload" }); }

self.addEventListener("install", function(e){
  e.waitUntil(
    caches.open(CACHE)
      .then(function(c){
        return c.addAll(CORE.map(fresh)).then(function(){
          return fetch(fresh("./data.json")).then(function(r){ return r.json(); }).then(function(d){
            var paths = {};
            (d.regions || []).forEach(function(r){
              (r.shops || []).forEach(function(s){ if (s.photo) paths[s.photo] = 1; });
              (r.photoSpots || []).forEach(function(s){ if (s.photo) paths[s.photo] = 1; });
            });
            if (d.hotel && d.hotel.photo) paths[d.hotel.photo] = 1;
            Object.keys(d.brands || {}).forEach(function(bid){
              (d.brands[bid].locations || []).forEach(function(loc){ if (loc.photo) paths[loc.photo] = 1; });
            });
            return Promise.all(Object.keys(paths).map(function(p){
              return fetch("./" + p).then(function(res){ if (res.ok) return c.put("./" + p, res); }).catch(function(){});
            }));
          });
        });
      })
      .catch(function(){})
      .then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function(e){
  e.waitUntil(
    caches.keys()
      .then(function(ks){ return Promise.all(ks.map(function(k){ return k === CACHE ? null : caches.delete(k); })); })
      .then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function(e){
  if (e.request.method !== "GET") return;
  if (e.request.url.indexOf("version.json") >= 0) return;
  if (e.request.url.indexOf("tile.openstreetmap.org") >= 0) return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: e.request.mode === "navigate" }).then(function(hit){
      if (hit) return hit;
      return fetch(e.request).then(function(res){
        var url = e.request.url;
        if (res.ok && (url.indexOf(self.location.origin) === 0 || url.indexOf("https://cdnjs.cloudflare.com/") === 0)){
          var copy = res.clone();
          caches.open(CACHE).then(function(c){ c.put(e.request, copy); }).catch(function(){});
        }
        return res;
      }).catch(function(){ return caches.match("./index.html"); });
    })
  );
});
