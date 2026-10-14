(() => {
  'use strict';
  const key='sessiondna-sync-base-v1',allowed=k=>k==='sessiondna-planning-v1'||k.startsWith('sessiondna-feedback-v1-');
  function localItems(){const items={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(allowed(k))items[k]=JSON.parse(localStorage.getItem(k));}return items;}
  const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b),object=x=>x&&typeof x==='object'&&!Array.isArray(x);
  function merge(base,local,remote,path=''){
    if(equal(local,remote))return local;
    if(equal(local,base))return remote;
    if(equal(remote,base))return local;
    if(object(local)&&object(remote)&&(base===undefined||object(base))){const result={};for(const k of new Set([...Object.keys(base||{}),...Object.keys(local),...Object.keys(remote)])){const v=merge(base?.[k],local[k],remote[k],path+'/'+k);if(v!==undefined)result[k]=v;}return result;}
    throw Error('Deux versions différentes pour '+path+'. Exporte tes données sur les deux appareils avant de choisir la version à conserver. Aucune version n’a été écrasée.');
  }
  if(typeof module!=='undefined')module.exports={merge};
  if(typeof document==='undefined')return;
  const host=document.createElement('section');host.className='panel';host.id='device-sync';
  const title=document.createElement('h2');title.textContent='Mes données entre appareils';
  const note=document.createElement('p');note.textContent='Après enregistrement d’un formulaire, une sauvegarde sur le PC est tentée automatiquement. Le bouton permet aussi de récupérer les données d’un autre appareil. En cas de conflit ou de données distantes nouvelles, la récupération reste manuelle pour préserver tes saisies en cours. Le PC doit être allumé ; l’accès privé iPhone reste à configurer.';
  const button=document.createElement('button');button.textContent='Synchroniser les saisies enregistrées';
  const message=document.createElement('p');message.setAttribute('role','status');
  const reload=document.createElement('button');reload.textContent='Recharger pour afficher les données récupérées';reload.hidden=true;reload.onclick=()=>location.reload();
  host.append(title,note,button,message,reload);document.getElementById('calendar').after(host);
  let active=false,queued=false;
  async function synchronize(automatic=false){if(active){queued=true;return;}active=true;button.disabled=true;try{
    const local=localItems();
    const base=JSON.parse(localStorage.getItem(key)||'{}');
    const response=await fetch('/api/state',{cache:'no-store'});if(!response.ok)throw Error('Serveur de sauvegarde indisponible. Démarre la nouvelle version de serve_sessiondna.py.');
    const remote=await response.json();if(!object(remote.items)||typeof remote.revision!=='string')throw Error('Réponse serveur invalide');
    const items=merge(base,local,remote.items);
    if(automatic&&!equal(items,local))throw Error('Des données existent sur le PC. Termine tes saisies puis utilise le bouton Synchroniser pour les récupérer.');
    if(!equal(local,localItems()))throw Error('Une saisie a changé pendant le transfert. Relance la synchronisation.');
    const saved=await fetch('/api/state',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:remote.revision,items})});
    if(!saved.ok){const error=await saved.json();throw Error(error.error||'Sauvegarde refusée');}
    if(!equal(local,localItems()))throw Error('Le PC a sauvegardé la version précédente ; une saisie plus récente reste dans ce navigateur. Relance la synchronisation.');
    // Les fichiers serveur sont déjà sauvegardés si le stockage navigateur échoue ensuite.
    for(const [k,v] of Object.entries(items)){if(!allowed(k)||!object(v))throw Error('Clé de sauvegarde invalide');localStorage.setItem(k,JSON.stringify(v));}
    for(const k of Object.keys(local))if(!Object.hasOwn(items,k))localStorage.removeItem(k);
    localStorage.setItem(key,JSON.stringify(items));
    message.textContent=automatic?'Sauvegarde automatique sur le PC réussie.':'Sauvegarde sur le PC réussie. Recharge la page pour afficher les données récupérées. Fais la même synchronisation sur l’autre appareil.';reload.hidden=automatic;
  }catch(e){message.textContent='Synchronisation interrompue : '+e.message;}finally{active=false;button.disabled=false;if(queued){queued=false;setTimeout(()=>synchronize(true),800);}}}
  button.addEventListener('click',()=>synchronize(false));
  let timer;const schedule=()=>{clearTimeout(timer);timer=setTimeout(()=>synchronize(true),800);};
  window.addEventListener('planning-change',schedule);
  window.addEventListener('feedback-change',schedule);
  window.addEventListener('online',schedule);
  try{if(Object.keys(localItems()).length)schedule();}catch(e){message.textContent='Données locales illisibles : aucune sauvegarde automatique effectuée.';}
})();
