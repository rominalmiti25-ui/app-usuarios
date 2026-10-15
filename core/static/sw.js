// Service worker mínimo: hace la app instalable sin guardar nada en caché,
// así las vistas protegidas nunca quedan almacenadas (respeta el no-store del backend).
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  e.respondWith(fetch(e.request).catch(() =>
    e.request.mode === 'navigate'
      ? new Response('<meta name="viewport" content="width=device-width"><body style="font-family:sans-serif;padding:2rem">Sin conexión a internet. Revisa tu red e inténtalo de nuevo.</body>',
                     {headers: {'Content-Type': 'text/html; charset=utf-8'}, status: 503})
      : Response.error()));
});
