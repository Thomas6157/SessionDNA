// Pas de mise en cache persistante des données sportives privées.
// Le service worker fournit le point d'entrée PWA ; une connexion au serveur reste nécessaire.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
