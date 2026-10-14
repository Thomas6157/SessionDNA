import {useEffect,useState} from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import {useQuery} from '@tanstack/react-query';
import {motion,useReducedMotion} from 'motion/react';
import {Activity,ArrowUpRight,CalendarDays,CheckCheck,Cloud,CloudOff,Compass,HeartPulse,Home,Leaf,RefreshCw,Settings as SettingsIcon,ShieldCheck} from 'lucide-react';
import type {Bootstrap,Feedback,JournalEntry,Session,TrainingWeek} from './types';
import {api} from './lib/api';
import {day,duration,monday,todayParis,weekDates} from './lib/format';
import {useStateStore} from './lib/state';
import {courses,clock} from './lib/planner';
import {planningTimes} from './lib/training';
import {Empty,Message,Modal,SessionCard,Stat} from './components';
import {SessionDetail,feedbackKey} from './SessionDetail';
import WeekPlanner,{getPlanning} from './WeekPlanner';
import Activities from './Activities';
import InsightsPanel from './InsightsPanel';
import Settings from './Settings';

const navigation=[{id:'today',label:'Aujourd’hui',icon:Home},{id:'week',label:'Semaine',icon:CalendarDays},{id:'activities',label:'Activités',icon:Activity},{id:'insights',label:'Bilan',icon:HeartPulse},{id:'settings',label:'Réglages',icon:SettingsIcon}];

export default function App(){
 const store=useStateStore(),reduced=useReducedMotion();
 const bootstrap=useQuery({queryKey:['bootstrap'],queryFn:()=>api<Bootstrap>('/api/bootstrap')});
 const [tab,setTab]=useState('today'),[selectedWeek,setSelectedWeek]=useState(''),[session,setSession]=useState<Session|null>(null),[conflictError,setConflictError]=useState('');
 const data=bootstrap.data,allWeeks=[...(data?.training_weeks||[])].sort((a,b)=>b.plan.week_start.localeCompare(a.plan.week_start));
 const currentWeek=monday(todayParis()),week=allWeeks.find(w=>w.plan.week_start===(selectedWeek||currentWeek))||allWeeks[0];
 const weekStart=week?.plan.week_start||selectedWeek||currentWeek;
 async function resolve(side:'local'|'remote'){try{await store.resolve(side);setConflictError('');}catch(e){setConflictError(e instanceof Error?e.message:'Résolution impossible. Tes saisies sont conservées.');}}
 return <Tabs.Root className="app-shell" value={tab} onValueChange={setTab}>
  <a className="skip-link" href="#main">Aller au contenu</a>
  <aside className="sidebar"><a className="brand" href="#" onClick={e=>{e.preventDefault();setTab('today');}} aria-label="SessionDNA, accueil"><span className="brand-mark"><Activity size={25}/></span><span>SESSION<span className="brand-light">DNA</span><small>TON QUOTIDIEN. TON TRIATHLON.</small></span></a>
   <span className="sidebar-caption">ESPACE PERSONNEL</span><Tabs.List className="navigation" aria-label="Navigation principale">{navigation.map(({id,label,icon:Icon})=><Tabs.Trigger value={id} key={id}><Icon size={21}/><span>{label}</span>{id==='insights'&&<span className="nav-dot"/>}</Tabs.Trigger>)}</Tabs.List>
   <div className="sidebar-bottom"><div className="journey-symbol"><Compass size={33}/></div><h3>Chaque jour compte.</h3><p>Un plan, tes sensations et la place de progresser.</p><div className="private-label"><ShieldCheck size={14}/>Espace personnel privé</div></div>
  </aside>
  <div className="main-shell"><header className="topbar"><div className="topbar-title"><span className="live-dot"/><span>Préparation triathlon</span></div><div className="topbar-actions">{allWeeks.length>0&&<label className="week-selector"><span className="sr-only">Semaine du programme</span><CalendarDays size={16}/><select value={weekStart} onChange={e=>{setSelectedWeek(e.target.value);setSession(null);}}>{allWeeks.map(w=><option key={w.manifest.source_sha256} value={w.plan.week_start}>Semaine du {day(w.plan.week_start)}</option>)}</select></label>}<button className={'sync-indicator '+(store.pending?'pending':'')} title={store.status} onClick={()=>void store.sync()} aria-label={'Synchroniser : '+store.status}>{store.pending?<CloudOff size={17}/>:<Cloud size={17}/>}<span>{store.pending?'En attente':'Sauvegarde'}</span></button><span className="avatar" aria-label="Espace personnel">T</span></div></header>
   <main id="main" tabIndex={-1}>
    {store.recovery&&<Message error>{store.recovery}<button className="text-button" onClick={store.backup}>Exporter les données à récupérer</button></Message>}
    {bootstrap.isPending?<Empty>Ton espace se prépare…</Empty>:bootstrap.error?<><Message error>Impossible de charger l’application : {bootstrap.error.message}</Message><button className="primary" onClick={()=>void bootstrap.refetch()}><RefreshCw size={17}/>Réessayer</button></>:data&&<>
     <Tabs.Content value="today"><motion.div initial={reduced?false:{opacity:0,y:9}} animate={{opacity:1,y:0}} transition={{duration:.23}}><Today data={data} week={week} onSelect={setSession} onNavigate={setTab}/></motion.div></Tabs.Content>
     <Tabs.Content value="week">{week?<WeekPlanner key={week.manifest.source_sha256} data={data} week={week} onSelect={setSession}/>:<NoPlan onNavigate={setTab}/>}</Tabs.Content>
     <Tabs.Content value="activities"><Activities/></Tabs.Content>
     <Tabs.Content value="insights"><InsightsPanel key={weekStart} week={weekStart}/></Tabs.Content>
     <Tabs.Content value="settings"><Settings data={data}/></Tabs.Content>
    </>}
   </main><footer className="app-footer"><span>SessionDNA · Fait pour durer.</span><span>{data?.generated_utc?'Données du '+day(data.generated_utc):'Tes données restent personnelles'}</span></footer>
  </div>
  {session&&week&&<SessionDetail key={week.manifest.source_sha256+session.id} session={session} week={week} onClose={()=>setSession(null)}/>}
  <Modal open={!!store.conflict} onClose={()=>{}} title="Deux versions à départager" description="Tes modifications et celles du serveur ont changé le même champ."><p>Aucune version n’a été écrasée. Exporte d’abord une sauvegarde pour examiner les deux versions, puis choisis celle à conserver. Le choix exporte aussi une copie du conflit.</p><p className="small">Champ concerné : {store.conflict?.path}</p><div className="button-row"><button className="secondary" onClick={store.backup}>Exporter mes saisies</button><button className="primary" onClick={()=>void resolve('local')}>Conserver mes saisies</button><button className="secondary" onClick={()=>void resolve('remote')}>Conserver celles du serveur</button></div>{conflictError&&<Message error>{conflictError}</Message>}</Modal>
 </Tabs.Root>;
}

function NoPlan({onNavigate}:{onNavigate:(s:string)=>void}){return <section className="panel welcome"><Compass size={42}/><h1>Ta prochaine semaine commence ici.</h1><p>Importe le programme JSON préparé dans ta conversation IRON MAN pour retrouver chaque séance et ses blocs.</p><button className="primary" onClick={()=>onNavigate('settings')}>Importer mon programme<ArrowUpRight size={18}/></button></section>;}

function Today({data,week,onSelect,onNavigate}:{data:Bootstrap;week?:TrainingWeek;onSelect:(s:Session)=>void;onNavigate:(tab:string)=>void}){
 const store=useStateStore(),today=todayParis();
 const feedback=week?(store.items[feedbackKey(week)]||{}) as Record<string,Feedback>:{};
 const inWeek=week?weekDates(week.plan.week_start).includes(today):false;
 const date=inWeek?today:week?.plan.week_start||today;
 const sessions=week?.plan.sessions||[],daily=sessions.filter(s=>s.date===date),planning=getPlanning(store.items,data),times=planningTimes(planning,week);
 const done=sessions.filter(s=>['done','modified'].includes(feedback[s.id]?.status)).length,answered=sessions.filter(s=>feedback[s.id]&&feedback[s.id].status!=='planned').length;
 const planned=sessions.reduce((sum,s)=>sum+(s.planned_duration_min||0),0);
 const coursesToday=courses(data.calendar?.events||[],date);
 const days=weekDates(week?.plan.week_start||monday(today));
 const sportVolumes=['swimming','cycling','running'].map(sport=>({sport,value:sessions.filter(s=>s.sport===sport).reduce((n,s)=>n+(s.planned_duration_min||0),0)}));
 const recentWeeks=data.weeks.filter(w=>w.week===(week?.plan.week_start||monday(today)));
 return <><div className="section-heading page-intro"><div><span className="eyebrow">{inWeek?'Aujourd’hui':week?'Semaine sélectionnée':'Ton espace triathlon'} · {day(date,true)}</span><h1>Le cap est donné.<br/><span className="muted-heading">À toi de jouer.</span></h1></div><span className="day-badge"><Leaf size={18}/>Avancer à ton rythme</span></div>
 <section className="hero"><div className="hero-copy"><span className="eyebrow light">{week?.plan.goal?.event_name||'PRÉPARATION IRONMAN'}</span><h2>De l’intention<br/>à chaque séance.</h2><p>{week?.plan.weekly_focus||'Tes entraînements, tes cours et tes sensations réunis dans un même espace.'}</p><button className="hero-button" onClick={()=>onNavigate(week?'week':'settings')}>{week?'Voir mon programme':'Importer mon programme'}<ArrowUpRight size={19}/></button></div><div className="hero-visual" aria-hidden><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="hero-score"><span>OBJECTIF SEMAINE</span><strong>{week?duration(planned):'À écrire'}</strong><div className="hero-sports">{sportVolumes.map(s=><span key={s.sport}><i className={s.sport}/>{duration(s.value)}</span>)}</div></div><span className="hero-axis">SWIM. BIKE. RUN. REPEAT.</span></div></section>
 {!week?<NoPlan onNavigate={onNavigate}/>:<>{!inWeek&&<Message>Ce programme ne couvre pas aujourd’hui. L’aperçu présente le premier jour de la semaine sélectionnée.</Message>}<div className="stats four overview-stats"><Stat label="Séances réalisées" value={<>{done}<em> / {sessions.length}</em></>} detail="D’après tes retours"/><Stat label="Volume programmé" value={duration(planned)} detail="Tous les sports et renforcement"/><Stat label="Volume enregistré" value={duration(recentWeeks.reduce((n,w)=>n+w.timer_min,0))} detail="Durée active des activités Garmin"/><Stat label="Retours à compléter" value={sessions.length-answered} detail="Chaque ressenti aide le prochain bilan"/></div>
 <div className="dashboard-grid"><section><div className="section-heading"><div><span className="eyebrow">LE PROCHAIN PAS</span><h2>{inWeek?'Au programme aujourd’hui':'Au programme le '+day(date)}</h2></div><button className="text-button" onClick={()=>onNavigate('week')}>La semaine<ArrowUpRight size={17}/></button></div><div className="today-sessions">{daily.length?daily.map(s=><SessionCard session={s} key={s.id} time={times[s.id]} feedback={feedback[s.id]} onClick={()=>onSelect(s)}/>):<div className="rest-day panel"><Leaf size={29}/><h3>Une journée pour récupérer.</h3><p>Aucune séance dans le programme pour cette date.</p></div>}</div>
 <section className="panel weekly-rhythm"><div className="section-heading"><h3>Le rythme de la semaine</h3><CheckCheck size={20}/></div><div className="rhythm-bars">{days.map(date=>{const ss=sessions.filter(s=>s.date===date),total=ss.reduce((n,s)=>n+(s.planned_duration_min||0),0);const max=Math.max(1,...days.map(d=>sessions.filter(s=>s.date===d).reduce((n,s)=>n+(s.planned_duration_min||0),0)));return <div key={date} className={date===today?'today':''}><span>{total?duration(total):'Repos'}</span><div className="rhythm-track" aria-label={day(date)+' : '+duration(total)}>{ss.map(s=><i className={s.sport} key={s.id} style={{height:Math.max(2,(s.planned_duration_min||0)/max*95)+'%'}}/>)}</div><strong>{day(date).split(' ')[0]}</strong></div>;})}</div></section></section>
 <aside className="dashboard-aside"><section className="panel"><div className="section-heading"><h3>À côté du sport</h3><CalendarDays size={21}/></div>{coursesToday.length?coursesToday.map((c,i)=><div className="agenda-item" key={i}><span>{clock(c.start)}<small>{clock(c.end)}</small></span><div><strong>{c.title}</strong><p>{c.location||'Lieu non précisé'}</p></div></div>):<p className="small">Aucun cours dans l’export pour cette date.</p>}<p className="footnote">D’après le dernier fichier MyDevinci importé.</p></section><DailyJournal date={today}/><button className="review-card" onClick={()=>onNavigate('insights')}><div><span className="eyebrow">FAIRE LE POINT</span><h3>Ta semaine a une histoire.</h3><p>Prépare le bilan pour adapter la suite.</p></div><ArrowUpRight size={22}/></button></aside></div></>}
 </>;
}
function DailyJournal({date}:{date:string}){const store=useStateStore(),entries=(store.items['sessiondna-journal-v1']||{}) as Record<string,JournalEntry>,entry=entries[date];const [sleep,setSleep]=useState(entry?.sleep_hours?.toString()||''),[energy,setEnergy]=useState(entry?.energy?.toString()||''),[notes,setNotes]=useState(entry?.notes||''),[message,setMessage]=useState(''),[dirty,setDirty]=useState(false);useEffect(()=>{if(!dirty){setSleep(entry?.sleep_hours?.toString()||'');setEnergy(entry?.energy?.toString()||'');setNotes(entry?.notes||'');}},[entry,dirty]);return <section className="panel journal"><span className="eyebrow">LE CHECK-IN DU JOUR</span><h3>Comment tu te sens ?</h3><form onSubmit={e=>{e.preventDefault();try{store.save('sessiondna-journal-v1',{...entries,[date]:{date,sleep_hours:sleep===''?null:Number(sleep),energy:energy===''?null:Number(energy),notes,updated_at:new Date().toISOString()}});setDirty(false);setMessage('Ressenti enregistré.');}catch(e){setMessage(String(e));}}}><div className="form-grid"><label>Sommeil (h)<input type="number" min="0" max="24" step="0.25" value={sleep} onChange={e=>{setDirty(true);setSleep(e.target.value);}}/></label><label>Énergie / 10<input type="number" min="0" max="10" value={energy} onChange={e=>{setDirty(true);setEnergy(e.target.value);}}/></label><label className="wide">Une note<textarea rows={2} value={notes} onChange={e=>{setDirty(true);setNotes(e.target.value);}} placeholder="Une nuit courte, de bonnes jambes…" maxLength={12000}/></label><button className="secondary wide">Enregistrer mon ressenti</button></div>{message&&<p className="small" role="status">{message}</p>}</form></section>;}
