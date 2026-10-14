import {createContext,useCallback,useContext,useEffect,useRef,useState} from 'react';
import type {ReactNode} from 'react';
import {api,download} from './api';
import type {StateItems,SyncState} from '../types';
import {BASE,Conflict,equal,merge,object,persist,rawBackup,readBase,readState,validateItems} from './state-core';
export {merge,Conflict,allowed} from './state-core';
type ConflictState={local:StateItems;remote:SyncState;path:string;base:StateItems;generation:number};
type Context={items:StateItems;save:(key:string,value:unknown)=>void;sync:()=>Promise<boolean>;status:string;pending:boolean;recovery:string|null;conflict:ConflictState|null;resolve:(side:'local'|'remote')=>Promise<void>;backup:()=>void;restore:(file:File)=>Promise<void>};
const StateContext=createContext<Context|null>(null);
export function StateProvider({children}:{children:ReactNode}){
 const [initial]=useState(()=>{try{readBase(localStorage);return {items:readState(localStorage),error:null};}catch{return {items:{} as StateItems,error:'Une sauvegarde locale est illisible. Rien ne sera écrasé : exporte les données de récupération puis restaure une sauvegarde valide.'};}});
 const [items,setItems]=useState<StateItems>(initial.items),[recovery,setRecovery]=useState<string|null>(initial.error);
 const current=useRef(items),busy=useRef(false),generation=useRef(0),recoveryRef=useRef(initial.error),conflictRef=useRef<ConflictState|null>(null);
 const [status,setStatus]=useState(initial.error||'Connexion au stockage…'),[pending,setPending]=useState(false),[conflict,setConflict]=useState<ConflictState|null>(null);
 const apply=(next:StateItems)=>{persist(localStorage,next);current.current=next;setItems(previous=>equal(previous,next)?previous:next);};
 const sync=useCallback(async()=>{
  if(busy.current||recoveryRef.current||conflictRef.current)return false;
  busy.current=true;const version=generation.current;
  try{
   const remote=await api<SyncState>('/api/state');validateItems(remote.items);
   const local=current.current,base=readBase(localStorage);let combined:StateItems;
   try{combined=merge(base,local,remote.items) as StateItems;}catch(e){if(e instanceof Conflict){const found={local,remote,path:e.path,base,generation:generation.current};conflictRef.current=found;setConflict(found);setPending(true);setStatus('Conflit à résoudre — les deux versions sont conservées');return false;}throw e;}
   if(version!==generation.current){setPending(true);return false;}
   const saved=equal(combined,remote.items)?remote:await api<SyncState>('/api/state',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:remote.revision,items:combined})});validateItems(saved.items);
   if(version===generation.current){apply(saved.items);localStorage.setItem(BASE,JSON.stringify(saved.items));setPending(false);setStatus('Sauvegardé sur cet appareil et le serveur');return true;}
   let fresh:StateItems;
   try{fresh=merge(local,current.current,saved.items) as StateItems;}catch(e){if(e instanceof Conflict){const found={local:current.current,remote:saved,path:e.path,base:local,generation:generation.current};conflictRef.current=found;setConflict(found);setPending(true);setStatus('Conflit pendant l’envoi — les deux versions sont conservées');return false;}throw e;}
   apply(fresh);localStorage.setItem(BASE,JSON.stringify(saved.items));setPending(true);setStatus('Une nouvelle saisie attend son envoi');return false;
  }catch(e){setPending(true);setStatus(navigator.onLine?(e instanceof Error?e.message:'Serveur indisponible'):'Hors connexion · saisies conservées sur cet appareil');return false;}finally{busy.current=false;}
 },[]);
 const save=useCallback((key:string,value:unknown)=>{
  if(recoveryRef.current)throw Error(recoveryRef.current);const next={...current.current,[key]:value};validateItems(next);
  apply(next);generation.current++;setPending(true);setStatus('Enregistré ici · envoi en attente');
 },[]);
 useEffect(()=>{const timer=setTimeout(()=>void sync(),650);return()=>clearTimeout(timer);},[items,sync]);
 useEffect(()=>{const online=()=>void sync();window.addEventListener('online',online);const timer=setInterval(()=>{if(navigator.onLine&&!document.hidden)void sync();},30000);return()=>{window.removeEventListener('online',online);clearInterval(timer);};},[sync]);
 const backup=()=>{const data=recoveryRef.current?{schema_version:'sessiondna.recovery.v1',raw:rawBackup(localStorage)}:{schema_version:'sessiondna.backup.v2',items:current.current};download('sessiondna-sauvegarde-'+new Date().toISOString().slice(0,10)+'.json',JSON.stringify({...data,exported_utc:new Date().toISOString()},null,2));};
 const restore=async(file:File)=>{
  if(busy.current)throw Error('Un envoi est en cours. Réessaie dans quelques secondes.');
  const data=JSON.parse(await file.text());if(!object(data)||data.schema_version!=='sessiondna.backup.v2')throw Error('Format de sauvegarde SessionDNA v2 attendu');validateItems(data.items);
  backup();const next=recoveryRef.current?data.items:{...current.current,...data.items};
  apply(next);if(recoveryRef.current){try{readBase(localStorage);}catch{localStorage.setItem(BASE,'{}');}}
  generation.current++;recoveryRef.current=null;setRecovery(null);conflictRef.current=null;setConflict(null);setPending(true);setStatus('Saisies restaurées localement · synchronisation en attente');
 };
 const resolve=async(side:'local'|'remote')=>{
  const found=conflictRef.current;if(!found)return;if(busy.current)throw Error('Un envoi est déjà en cours.');busy.current=true;
  try{
   const remote=await api<SyncState>('/api/state');validateItems(remote.items);
   if(remote.revision!==found.remote.revision||generation.current!==found.generation){const updated={...found,local:current.current,remote,generation:generation.current};conflictRef.current=updated;setConflict(updated);throw Error('Une version a changé depuis l’ouverture. Les versions ont été actualisées ; vérifie ton choix avant de confirmer de nouveau.');}
   const archive=JSON.stringify(found,null,2);localStorage.setItem('sessiondna-conflict-'+Date.now(),archive);download('sessiondna-conflit-'+Date.now()+'.json',archive);
   const selected=merge(found.base,current.current,remote.items,'',side) as StateItems;
   const saved=equal(selected,remote.items)?remote:await api<SyncState>('/api/state',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:remote.revision,items:selected})});validateItems(saved.items);
   apply(saved.items);localStorage.setItem(BASE,JSON.stringify(saved.items));generation.current++;conflictRef.current=null;setConflict(null);setPending(false);setStatus('Conflit résolu ; les deux versions restent archivées sur cet appareil');
  }finally{busy.current=false;}
 };
 return <StateContext.Provider value={{items,save,sync,status,pending,recovery,conflict,resolve,backup,restore}}>{children}</StateContext.Provider>;
}
export function useStateStore(){const v=useContext(StateContext);if(!v)throw Error('StateProvider manquant');return v;}
