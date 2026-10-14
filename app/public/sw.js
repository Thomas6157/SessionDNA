/* SessionDNA: private cache, no third-party requests. Mutations are never cached. */
const CACHE='sessiondna-shell-v2-__BUILD_ID__';
const SHELL=['/','/manifest.webmanifest','/icon.svg','/icon-192.png','/icon-512.png',/*PRECACHE_ASSETS*/];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('sessiondna-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);if(request.method!=='GET'||url.origin!==self.location.origin)return;
 const isApi=url.pathname.startsWith('/api/');
 if(isApi&&!['/api/bootstrap','/api/activities'].some(p=>url.pathname===p||url.pathname.startsWith(p+'/')))return;
 if(!isApi&&request.mode!=='navigate'&&!url.pathname.startsWith('/assets/')&&!['/','/manifest.webmanifest','/icon.svg','/icon-192.png','/icon-512.png'].includes(url.pathname))return;
 event.respondWith((async()=>{
  const cache=await caches.open(CACHE);
  try{const response=await fetch(request);if(response.ok){const copy=response.clone();event.waitUntil(cache.put(request,copy));}return response;}
  catch{const cached=await cache.match(request);if(cached)return cached;if(!isApi&&request.mode==='navigate'){const shell=await cache.match('/');if(shell)return shell;}return new Response(JSON.stringify({error:'Cette page n’a pas encore été consultée sur cet appareil.'}),{status:503,headers:{'Content-Type':'application/json'}});}
 })());
});
