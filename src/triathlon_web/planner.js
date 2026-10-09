/* Calculs en heures civiles Europe/Paris, indépendants du fuseau du téléphone. */
(function(root){
  'use strict';
  const mins=t=>{if(!/^\d{2}:\d{2}$/.test(t||''))return NaN;const [h,m]=t.split(':').map(Number);return h<24&&m<60?h*60+m:NaN;};
  const clock=n=>`${String(Math.floor(n/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}`;
  const overlap=(a,b)=>a.start<b.end&&b.start<a.end;
  function courses(events,date){return events.filter(e=>e.start.slice(0,10)<=date&&e.end.slice(0,10)>=date).map(e=>({...e,start:e.start.slice(0,10)<date?0:mins(e.start.slice(11,16)),end:e.end.slice(0,10)>date?1440:mins(e.end.slice(11,16))})).filter(e=>e.end>e.start);}
  function validate(p){return Number.isFinite(mins(p.wake))&&Number.isFinite(mins(p.bed))&&mins(p.bed)>mins(p.wake)&&['commute','before','after','swimExtra'].every(k=>p[k]!==''&&Number.isFinite(Number(p[k]))&&Number(p[k])>=0&&Number(p[k])<=240);}
  function interval(s,time,p){return {start:mins(time)-Number(p.before),end:mins(time)+s.planned_duration_min+Number(p.after)+(s.sport==='swimming'?Number(p.swimExtra):0)};}
  function conflicts(s,time,p,events,sessions,times,pool){
    const span=interval(s,time,p), reasons=[];
    if(!Number.isFinite(span.start)||!Number.isFinite(span.end))return ['Horaire ou durée invalide'];
    if(span.start<mins(p.wake)||span.end>mins(p.bed))reasons.push('Sommeil / limites de journée');
    if(s.sport==='swimming'&&pool){
      if(s.date<pool.valid_from||s.date>pool.valid_until)reasons.push('Horaires piscine à revérifier pour cette date');
      else {
        const hours=pool.hours[new Date(s.date+'T12:00:00Z').getUTCDay()];
        if(!hours||mins(time)<mins(hours[0])+pool.changing_min||mins(time)+s.planned_duration_min+Number(p.swimExtra)>mins(hours[1])-pool.evacuation_min)reasons.push('Piscine : ouverture, vestiaire ou évacuation des bassins');
      }
    }
    for(const c of courses(events,s.date))if(overlap(span,{start:c.start-Number(p.commute),end:c.end+Number(p.commute)}))reasons.push('Cours / trajet : '+c.title);
    for(const other of sessions)if(other.id!==s.id&&other.date===s.date&&times[other.id]&&overlap(span,interval(other,times[other.id],p)))reasons.push('Autre séance : '+other.title);
    return reasons;
  }
  const api={mins,clock,overlap,courses,validate,interval,conflicts};
  if(typeof module!=='undefined')module.exports=api;else root.SessionPlanner=api;
})(typeof window!=='undefined'?window:globalThis);
