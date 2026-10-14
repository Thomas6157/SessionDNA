import type {StateItems} from '../types';
export const CACHE='sessiondna-app-state-v2',BASE='sessiondna-sync-base-v1';
export const allowed=(k:string)=>k==='sessiondna-planning-v1'||k==='sessiondna-annotations-v2'||k==='sessiondna-journal-v1'||k.startsWith('sessiondna-feedback-v1-');
export const object=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export function equal(a:unknown,b:unknown):boolean{if(a===b)return true;if(Array.isArray(a)&&Array.isArray(b))return a.length===b.length&&a.every((v,i)=>equal(v,b[i]));if(object(a)&&object(b)){const keys=Object.keys(a);return keys.length===Object.keys(b).length&&keys.every(k=>Object.hasOwn(b,k)&&equal(a[k],b[k]));}return false;}
export class Conflict extends Error {constructor(public path:string){super('Deux modifications différentes : '+path);}}
export function merge(base:unknown,local:unknown,remote:unknown,path='',preference?:'local'|'remote'):unknown{
 if(equal(local,remote))return local;if(equal(local,base))return remote;if(equal(remote,base))return local;
 if(object(local)&&object(remote)&&(base===undefined||object(base))){const b=object(base)?base:{};const result:Record<string,unknown>={};for(const k of new Set([...Object.keys(b),...Object.keys(local),...Object.keys(remote)])){const v=merge(b[k],local[k],remote[k],path+'/'+k,preference);if(v!==undefined)result[k]=v;}return result;}
 if(preference)return preference==='local'?local:remote;
 throw new Conflict(path);
}
export function validateItems(value:unknown):asserts value is StateItems{if(!object(value)||Object.entries(value).some(([k,v])=>!allowed(k)||!object(v)))throw Error('Saisies SessionDNA invalides : aucune modification n’a été appliquée.');}
export function readState(storage:Storage):StateItems{
 const snapshot=storage.getItem(CACHE);const cached=JSON.parse(snapshot||'{}');validateItems(cached);
 // After migration the single snapshot is authoritative, even if writing a legacy mirror hit quota.
 if(snapshot!==null)return cached;
 const items:StateItems={};
 for(let i=0;i<storage.length;i++){const key=storage.key(i);if(key&&allowed(key)){const value=JSON.parse(storage.getItem(key)||'{}');if(!object(value))throw Error('Stockage invalide : '+key);items[key]=value;}}
 return items;
}
export function readBase(storage:Storage):StateItems{const base=JSON.parse(storage.getItem(BASE)||'{}');validateItems(base);return base;}
export function persist(storage:Storage,items:StateItems){
 validateItems(items);
 // Write the complete durable snapshot first. Do not remove legacy values unless it succeeds.
 storage.setItem(CACHE,JSON.stringify(items));
 const keys=Array.from({length:storage.length},(_,i)=>storage.key(i));
 try{for(const key of keys)if(key&&allowed(key)&&!Object.hasOwn(items,key))storage.removeItem(key);
 for(const[key,value]of Object.entries(items))storage.setItem(key,JSON.stringify(value));}catch{/* The complete authoritative snapshot was saved before these compatibility mirrors. */}
}
export function rawBackup(storage:Storage){const raw:Record<string,string|null>={};for(let i=0;i<storage.length;i++){const key=storage.key(i);if(key&&(allowed(key)||key===CACHE||key===BASE||key.startsWith('sessiondna-conflict-')))raw[key]=storage.getItem(key);}return raw;}
