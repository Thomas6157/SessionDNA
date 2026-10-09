/* Programme importé immuable ; retours saisis séparément et sauvegardés dans ce navigateur. */
(() => {
  'use strict';
  const data=window.SESSIONDNA, weeks=data.training_weeks||[], byId=id=>document.getElementById(id);
  const sports={running:'Course',cycling:'Vélo',swimming:'Natation',strength:'Renforcement',mobility:'Mobilité',other:'Autre'};
  const types={warmup:'Échauffement',work:'Effort',recovery:'Récupération',cooldown:'Retour au calme',drill:'Éducatif',rest:'Repos'};
  const statuses={planned:'Non renseignée',done:'Réalisée',modified:'Modifiée',skipped:'Non réalisée'};
  const node=(tag,text,cls)=>{const x=document.createElement(tag);if(text!=null)x.textContent=text;if(cls)x.className=cls;return x};
  const nfmt=n=>n==null?'—':Number(n).toLocaleString('fr-FR',{maximumFractionDigits:1});
  const minutes=n=>n==null?'Non précisée':`${Math.floor(n/60)} h ${String(Math.round(n%60)).padStart(2,'0')}`;
  const dateLabel=iso=>new Date(iso+'T12:00:00').toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'});
  const pace=n=>{const s=Math.round(n);return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;};
  const durationLabel=n=>n<60?nfmt(n)+' s':Math.floor(n/60)+' min'+(n%60?' '+nfmt(n%60)+' s':'');
  function range(v,unit='',formatter=nfmt){if(!v||(v.min==null&&v.max==null))return '';if(v.min==null)return '≤ '+formatter(v.max)+unit;if(v.max==null)return '≥ '+formatter(v.min)+unit;return (v.min===v.max?formatter(v.min):formatter(v.min)+'–'+formatter(v.max))+unit;}
  let current,feedback={},storeKey='',storageIssue='';
  if(!weeks.length){byId('training').hidden=true;return;}
  const selector=byId('training-week');
  for(const w of weeks){const option=node('option','Du '+dateLabel(w.plan.week_start));option.value=w.plan.week_start;selector.append(option)}
  const today=new Date().toLocaleDateString('en-CA',{timeZone:'Europe/Paris'});
  selector.value=weeks.filter(w=>w.plan.week_start<=today).at(-1)?.plan.week_start||weeks[0].plan.week_start;
  function plannedTime(id){try{return JSON.parse(localStorage.getItem('sessiondna-planning-v1')||'{}').weeks?.[current.manifest.source_sha256]?.[id]||null;}catch{return null;}}
  window.addEventListener('planning-change',()=>{if(current)render();});
  function message(text){byId('training-message').textContent=text;}
  function load(){
    current=weeks.find(w=>w.plan.week_start===selector.value);storeKey='sessiondna-feedback-v1-'+current.manifest.source_sha256;feedback={};storageIssue='';
    try{const saved=JSON.parse(localStorage.getItem(storeKey)||'{}');feedback=validateFeedback(saved);}catch(e){storageIssue='Lecture des retours impossible : '+e.message+' Les données existantes ne seront pas écrasées.';}
    byId('training-detail').hidden=true;byId('training-report-label').hidden=true;byId('training-report-download').hidden=true;message(storageIssue);render();
  }
  function validateFeedback(records){
    if(!records||typeof records!=='object'||Array.isArray(records))throw Error('format de sauvegarde invalide');
    const allowed=new Set(current.plan.sessions.map(s=>s.id)),result={};
    for(const [id,r] of Object.entries(records)){
      if(!allowed.has(id)||!r||typeof r!=='object'||!Object.hasOwn(statuses,r.status))throw Error('séance ou statut invalide');
      for(const [key,max] of [['actual_duration_min',1440],['rpe',10],['fatigue',10],['pain',10],['sleep_hours',24]])if(r[key]!=null&&(typeof r[key]!=='number'||!Number.isFinite(r[key])||r[key]<0||r[key]>max))throw Error('valeur invalide : '+key);
      if(typeof r.notes!=='string'||r.notes.length>20000)throw Error('commentaire invalide');
      if(!r.answers||typeof r.answers!=='object'||Array.isArray(r.answers)||Object.values(r.answers).some(v=>typeof v!=='string'||v.length>20000))throw Error('réponses invalides');
      if(r.activity_id!=null&&!data.activities.some(a=>a.id===r.activity_id))throw Error('activité Garmin absente de cet historique');
      result[id]=r;
    }
    return result;
  }
  function save(next){if(storageIssue)throw Error(storageIssue);localStorage.setItem(storeKey,JSON.stringify(next));feedback=next;window.dispatchEvent(new Event('feedback-change'));}
  function list(parent,title,items){if(!items?.length)return;const details=node('details'),summary=node('summary',title),ul=node('ul');for(const text of items)ul.append(node('li',text));details.append(summary,ul);parent.append(details);}
  function render(){
    const p=current.plan,overview=byId('training-overview');overview.replaceChildren();
    overview.append(node('p',(p.goal?.event_name||'Objectif personnel')+(p.goal?.event_date?' · '+p.goal.event_date:''),'goal-label'));
    const stats=node('div',null,'training-stats');for(const [name,filter] of [['Endurance',s=>['running','cycling','swimming'].includes(s.sport)],['Renforcement / mobilité',s=>['strength','mobility'].includes(s.sport)]]){const card=node('div');card.append(node('strong',minutes(p.sessions.filter(filter).reduce((a,s)=>a+(s.planned_duration_min||0),0))),node('span',name));stats.append(card)}
    const count=node('div');count.append(node('strong',p.sessions.length+' séances'),node('span',Object.values(feedback).filter(r=>['done','modified'].includes(r.status)).length+' renseignées comme réalisées'));stats.append(count);overview.append(stats,node('p',p.weekly_focus));
    overview.append(node('p','Programme fourni par ta conversation IRON MAN. Durées annoncées : elles ne constituent pas encore des créneaux avec trajets, préparation et récupérations.','planning-notice'));
    list(overview,'Notes de la semaine',p.planning_notes);list(overview,'Contraintes connues',p.athlete_context?.known_constraints);list(overview,'Points à confirmer',p.athlete_context?.unknowns_to_confirm);
    const days=byId('training-days');days.replaceChildren();
    for(let offset=0;offset<7;offset++){const date=new Date(p.week_start+'T12:00:00');date.setDate(date.getDate()+offset);const iso=[date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');const card=node('article',null,'training-day'),sessions=p.sessions.filter(s=>s.date===iso);card.append(node('h3',dateLabel(iso)));
      if(!sessions.length)card.append(node('p',p.rest_days.includes(iso)?'Repos prévu':'Aucune séance renseignée'));
      for(const s of sessions){const button=node('button',null,'session-card sport-'+s.sport);button.type='button';button.append(node('span',sports[s.sport],'session-sport'),node('strong',s.title),node('span',minutes(s.planned_duration_min)+(s.planned_distance_m?' · '+nfmt(s.planned_distance_m/1000)+' km':'')),node('small',range(s.target_session_rpe)?'RPE attendu '+range(s.target_session_rpe)+'/10':'RPE global non renseigné'),node('span',statuses[feedback[s.id]?.status||'planned'],'session-status'));if(plannedTime(s.id))button.append(node('small','Horaire choisi : '+plannedTime(s.id)+' (Paris)'));button.addEventListener('click',()=>detail(s));card.append(button)}days.append(card);}
  }
  function detail(s){
    const panel=byId('training-detail');panel.hidden=false;panel.replaceChildren(node('span',sports[s.sport]+' · '+dateLabel(s.date),'eyebrow'),node('h2',s.title),node('p',s.objective));
    panel.append(node('p',minutes(s.planned_duration_min)+' annoncées · '+(range(s.target_session_rpe)?'RPE '+range(s.target_session_rpe)+'/10':'RPE global non renseigné')));
    const audit=current.manifest.audit.sessions.find(x=>x.id===s.id);list(panel,'Contrôle des données importées',audit?.notes);
    const blocks=node('div',null,'workout-blocks');
    for(const b of s.blocks){const block=node('article',null,'workout-block');block.append(node('h3',(b.repeat>1?b.repeat+' × ':'')+b.name));const steps=node('ol');
      for(const t of b.steps){const step=node('li'),measure=[t.duration_sec!=null?durationLabel(t.duration_sec):null,t.distance_m!=null?nfmt(t.distance_m)+' m':null].filter(Boolean).join(' · ');step.append(node('strong',(types[t.type]||t.type)+(measure?' · '+measure:'')));
        const targets=[range(t.target_rpe,'/10')&&'RPE '+range(t.target_rpe,'/10'),range(t.target_power_w,' W'),range(t.target_heart_rate_bpm,' bpm'),range(t.target_pace_sec_per_km,' /km',pace),range(t.target_pace_sec_per_100m,' /100 m',pace)].filter(Boolean);if(targets.length)step.append(node('p',targets.join(' · '),'step-targets'));step.append(node('p',t.instructions||''));steps.append(step)}block.append(steps);blocks.append(block)}panel.append(blocks);
    const linked=current.plan.sessions.find(x=>x.id===s.scheduling.linked_session_id);if(linked)panel.append(node('p','Séance liée : '+linked.title+' ('+linked.date+'). Voir les contraintes d’ordre ci-dessous.'));
    panel.append(node('p',plannedTime(s.id)?'Horaire choisi : '+plannedTime(s.id)+' (Paris). Voir Cours et horaires pour les conflits.':'Horaire non fixé : ouvre Cours et horaires pour le choisir.'));
    list(panel,'Contraintes de placement',s.scheduling.constraints);list(panel,'Matériel',s.equipment);list(panel,'Consignes complètes',s.execution_notes);list(panel,'Adaptations prévues dans le programme',s.adjustment_options);
    form(panel,s);panel.scrollIntoView({behavior:'smooth'});panel.focus({preventScroll:true});
  }
  function form(parent,s){
    parent.append(node('h3','Mon retour de séance'));const f=node('form',null,'feedback-form'),r=feedback[s.id]||{},controls={};
    function field(key,title,tag='input',type='text'){const label=node('label',title),input=node(tag);input.name=key;if(tag==='input')input.type=type;label.append(input);f.append(label);controls[key]=input;return input;}
    const status=field('status','État de la séance','select');for(const [value,title] of Object.entries(statuses)){const o=node('option',title);o.value=value;status.append(o)}status.value=r.status||'planned';
    for(const [key,title,max] of [['actual_duration_min','Durée réellement effectuée (min)',1440],['rpe','RPE ressenti (0–10)',10],['fatigue','Fatigue après séance (0–10)',10],['pain','Douleur maximale ressentie (0–10)',10],['sleep_hours','Sommeil de la nuit précédente (h)',24]]){const input=field(key,title,'input','number');input.min='0';input.max=String(max);input.step='0.1';input.value=r[key]??'';}
    const activity=field('activity_id','Associer une activité Garmin (facultatif)','select'),none=node('option','Aucune association');none.value='';activity.append(none);for(const a of data.activities.filter(a=>a.sport===s.sport&&Math.abs((new Date(a.start_utc)-new Date(s.date+'T12:00:00'))/86400000)<1.5).sort((a,b)=>b.start_utc.localeCompare(a.start_utc))){const o=node('option',new Date(a.start_utc).toLocaleDateString('fr-FR')+' · '+nfmt(a.timer_min)+' min · '+a.filename);o.value=a.id;activity.append(o)}activity.value=r.activity_id||'';
    const comment=field('notes','Commentaire et changements effectués','textarea');comment.value=r.notes||'';comment.rows=3;comment.maxLength=20000;
    const answers={};for(const [i,q] of (s.feedback_questions||[]).entries()){const input=field('answer_'+i,q,'textarea');input.rows=2;input.maxLength=20000;input.value=r.answers?.[q]||'';answers[q]=input;}
    const submit=node('button','Enregistrer mon retour','primary-button');submit.type='submit';const saved=node('p',null,'save-status');saved.setAttribute('role','status');f.append(submit,saved);
    f.addEventListener('submit',event=>{event.preventDefault();if(!f.reportValidity())return;try{const record={status:status.value,notes:comment.value,activity_id:activity.value||null,answers:Object.fromEntries(Object.entries(answers).map(([q,input])=>[q,input.value])),updated_at:new Date().toISOString()};for(const key of ['actual_duration_min','rpe','fatigue','pain','sleep_hours'])record[key]=controls[key].value===''?null:Number(controls[key].value);const next={...feedback,[s.id]:record};validateFeedback(next);save(next);saved.textContent='Retour enregistré dans ce navigateur. Pense à exporter tes retours.';render();}catch(e){saved.textContent='Sauvegarde impossible : '+e.message;}});parent.append(f);
  }
  function report(){
    const p=current.plan,lines=['# Bilan SessionDNA — semaine du '+p.week_start,'','Programme source : '+current.manifest.source_sha256,'','## Retours par séance'];
    for(const s of p.sessions){const r=feedback[s.id];lines.push('',`### ${s.date} — ${s.title} (${sports[s.sport]})`,`Prévu : ${s.planned_duration_min??'non précisé'} min ; RPE ${range(s.target_session_rpe)||'non renseigné'}.`);if(plannedTime(s.id))lines.push('Horaire choisi : '+plannedTime(s.id)+' (Europe/Paris).');if(!r){lines.push('Retour non renseigné : ne pas interpréter comme une séance manquée.');continue;}lines.push('État déclaré : '+statuses[r.status],`Durée déclarée : ${r.actual_duration_min??'non renseignée'} min ; RPE : ${r.rpe??'non renseigné'} ; fatigue : ${r.fatigue??'non renseignée'} ; douleur : ${r.pain??'non renseignée'} ; sommeil : ${r.sleep_hours??'non renseigné'} h.`);const activity=data.activities.find(a=>a.id===r.activity_id);if(activity)lines.push(`Garmin associé manuellement : ${activity.filename}, ${nfmt(activity.timer_min)} min, ${nfmt(activity.distance_km)} km.`);if(r.notes)lines.push('Commentaire : '+r.notes);for(const [q,a] of Object.entries(r.answers))lines.push(q+' '+(a||'Non renseigné.'));}
    lines.push('','## Questions du bilan prévu',...(p.weekly_review_questions||[]).map(q=>'- '+q),'','Les champs absents sont inconnus. Ce bilan ne modifie pas automatiquement le programme suivant.');return lines.join('\n');
  }
  function download(name,text,type){const url=URL.createObjectURL(new Blob([text],{type})),a=node('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  byId('training-report').addEventListener('click',()=>{byId('training-report-label').hidden=false;byId('training-report-download').hidden=false;byId('training-report-text').value=report();});
  byId('training-report-download').addEventListener('click',()=>download('bilan-'+current.plan.week_start+'.md',report(),'text/markdown;charset=utf-8'));
  byId('training-backup').addEventListener('click',()=>download('retours-'+current.plan.week_start+'.json',JSON.stringify({schema_version:'sessiondna.feedback.v1',week_start:current.plan.week_start,source_sha256:current.manifest.source_sha256,feedback},null,2),'application/json'));
  byId('training-restore').addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file)return;if(file.size>2e6)throw Error('fichier trop volumineux');const payload=JSON.parse(await file.text());if(payload.schema_version!=='sessiondna.feedback.v1'||payload.week_start!==current.plan.week_start||payload.source_sha256!==current.manifest.source_sha256)throw Error('ce fichier correspond à une autre semaine ou version du programme');const restored=validateFeedback(payload.feedback);let added=0,skipped=0;const next={...feedback};for(const [id,r] of Object.entries(restored)){if(Object.hasOwn(next,id)){skipped++;continue;}next[id]=r;added++;}save(next);render();byId('training-detail').hidden=true;message(added+' retours restaurés ; '+skipped+' déjà présents conservés.');}catch(e){message('Import des retours refusé : '+e.message);}finally{event.target.value='';}});
  selector.addEventListener('change',load);load();
})();
