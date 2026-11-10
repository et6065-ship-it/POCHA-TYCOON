// Service Worker for Unified Standalone Home Screen WebApp (PWA)
const CACHE_NAME = 'game-launcher-pwa-v5';
const CORE_SHELL_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './src/css/launcher.css',
  './src/js/launcher_common.js',
  './src/js/launcher.js',
  './assets/icons/icon-launcher-192.png',
  './assets/icons/apple-touch-icon.png'
];

const OFFLINE_FALLBACK_HTML =
  '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8" />' +
  '<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover" />' +
  '<title>오프라인 안내</title>' +
  '<style>body{margin:0;min-height:100dvh;display:flex;align-items:center;justify-content:center;background:#090c15;color:#f8fafc;font-family:sans-serif;padding:20px;text-align:center}' +
  '.box{max-width:360px;background:#111626;border:3px solid #f5b700;padding:22px;border-radius:12px}' +
  'h1{font-size:18px;color:#fde047;margin:0 0 10px}p{font-size:13px;color:#cbd5e1;line-height:1.5;margin:0 0 18px}' +
  'button{padding:10px 16px;background:#059669;color:#fff;border:2px solid #34d399;border-radius:8px;font-weight:800;font-size:13px;cursor:pointer}</style>' +
  '</head><body><div class="box"><h1>📡 오프라인 상태입니다</h1>' +
  '<p>이 게임은 아직 오프라인 캐시에 저장되지 않았습니다. 온라인 상태에서 한 번 실행하면 오프라인에서도 플레이할 수 있습니다.</p>' +
  '<button type="button" id="btn-back">🎮 런처로 돌아가기</button></div>' +
  '<script>document.getElementById("btn-back").onclick=function(){if(window.parent!==window){try{window.parent.postMessage({type:"LAUNCHER_RETURN"},location.protocol==="file:"?"*":location.origin);return;}catch(e){}}location.replace("./");};</script>' +
  '</body></html>';

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(CORE_SHELL_ASSETS);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.map(function (k) {
          if (k !== CACHE_NAME) return caches.delete(k);
        })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET') return;

  var reqUrl;
  try {
    reqUrl = new URL(event.request.url);
  } catch (e) {
    return;
  }
  if (reqUrl.origin !== self.location.origin) return;

  event.respondWith(
    fetch(event.request)
      .then(function (response) {
        if (response && response.status === 200 && response.type === 'basic') {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(event.request, clone);
          }).catch(function () {});
        }
        return response;
      })
      .catch(function () {
        return caches.match(event.request).then(function (exact) {
          if (exact) return exact;
          return caches.match(event.request, { ignoreSearch: true });
        }).then(function (matched) {
          if (matched) return matched;
          var accept = event.request.headers.get('accept') || '';
          if (event.request.mode === 'navigate' || accept.indexOf('text/html') !== -1) {
            return new Response(OFFLINE_FALLBACK_HTML, {
              status: 503,
              headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
          }
          return new Response('Offline', {
            status: 503,
            headers: { 'Content-Type': 'text/plain; charset=utf-8' }
          });
        });
      })
  );
});
