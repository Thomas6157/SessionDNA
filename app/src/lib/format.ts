import type {Range} from '../types';
export const sports:Record<string,string>={running:'Course',cycling:'Vélo',swimming:'Natation',strength:'Renforcement',mobility:'Mobilité',hiking:'Randonnée',other:'Autre'};
export const objectives:Record<string,string>={ef:'Footing / EF',recuperation:'Récupération',endurance_soutenue:'Endurance soutenue',seuil:'Seuil',vo2max:'VO₂ max',vitesse:'Vitesse / sprints',competition:'Compétition',autre:'Autre',incertain:'Incertain'};
export const formats:Record<string,string>={continu:'Continu',progressif:'Progressif',intervalles_courts:'Intervalles courts',intervalles_longs:'Intervalles longs',mixte:'Mixte',incertain:'Incertain'};
export const statuses:Record<string,string>={planned:'À renseigner',done:'Réalisée',modified:'Adaptée',skipped:'Non réalisée'};
export const num=(n:number|null|undefined,d=1)=>n==null?'—':Number(n).toLocaleString('fr-FR',{maximumFractionDigits:d});
export const duration=(n:number|null|undefined)=>{if(n==null||!Number.isFinite(n))return 'Durée inconnue';const rounded=Math.round(n);return rounded<60?`${rounded} min`:`${Math.floor(rounded/60)} h${rounded%60?' '+String(rounded%60).padStart(2,'0'):''}`;};
export const day=(date:string,long=false)=>new Date(date.includes('T')?date:date+'T12:00:00Z').toLocaleDateString('fr-FR',{timeZone:'Europe/Paris',weekday:long?'long':'short',day:'numeric',month:long?'long':'short'});
export const todayParis=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export function weekDates(start:string){return Array.from({length:7},(_,i)=>{const d=new Date(start+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+i);return d.toISOString().slice(0,10);});}
export function monday(date:string){const d=new Date(date+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));return d.toISOString().slice(0,10);}
export const range=(r?:Range,unit='')=>!r||(r.min==null&&r.max==null)?'':r.min==null?`≤ ${num(r.max)}${unit}`:r.max==null?`≥ ${num(r.min)}${unit}`:r.min===r.max?`${num(r.min)}${unit}`:`${num(r.min)}–${num(r.max)}${unit}`;
export const pace=(s:number)=>`${Math.floor(Math.round(s)/60)}:${String(Math.round(s)%60).padStart(2,'0')}`;
export const paceRange=(r:Range,unit:string)=>`${r.min==null?'':pace(r.min)}${r.min!=null&&r.max!=null&&r.min!==r.max?'–':''}${r.max!=null&&r.min!==r.max?pace(r.max):''}${unit}`;
