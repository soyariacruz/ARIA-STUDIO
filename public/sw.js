/* ARIA STUDIO · service worker (v375): solo los avisos (push). No guarda nada en caché: la web siempre se carga nueva del servidor. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
const IOS = /iPhone|iPad|iPod/.test(self.navigator.userAgent || '');
self.addEventListener('push', e => {
  let d = {}; try { d = e.data ? e.data.json() : {}; } catch (er) { d = { cuerpo: e.data ? e.data.text() : '' }; }
  e.waitUntil((async () => {
    const W = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const delante = W.find(c => c.focused && c.visibilityState === 'visible');
    if (delante && !IOS) { delante.postMessage({ aviso: d }); return; }   // con la web delante ya avisa ella (sonido + su notificación): no se repite
    await self.registration.showNotification(d.titulo || 'ARIA STUDIO', { body: d.cuerpo || '', tag: d.tag || 'aria', renotify: true, icon: '/pwa/icono-192.png', badge: '/pwa/icono-96.png', data: { con: d.con || '' } });
  })());
});
self.addEventListener('notificationclick', e => {
  e.notification.close(); const con = (e.notification.data || {}).con || '';
  e.waitUntil((async () => {
    const W = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    if (W.length) { const c = W[0]; await c.focus(); c.postMessage({ abre: con }); return; }
    await self.clients.openWindow('/?app=1' + (con ? '&aviso=' + encodeURIComponent(con) : ''));
  })());
});
