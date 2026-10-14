import type {Planning,Session,TrainingWeek} from '../types';

// Hours belong to the exact imported version, like the session feedback.
export const planningTimes=(planning:Planning,week?:TrainingWeek)=>
  week ? planning.weeks[week.manifest.source_sha256]||{} : {};

export const isLinked=(session:Session,sessions:Session[])=>
  !!session.scheduling.linked_session_id || sessions.some(other=>other.scheduling.linked_session_id===session.id);

export function stepDuration(seconds:number){
  if(!Number.isFinite(seconds)||seconds<0)return 'Durée inconnue';
  const total=Math.round(seconds),minutes=Math.floor(total/60),rest=total%60;
  return [minutes?`${minutes} min`:'',rest||!minutes?`${rest} s`:''].filter(Boolean).join(' ');
}

export const questionValues=(questions:string[],answers:Record<string,string>={})=>
  questions.map((question,index)=>answers[question]??answers['q'+index]??'');

export function questionAnswers(questions:string[],values:string[],previous:Record<string,string>={}){
  const result={...previous};
  questions.forEach((question,index)=>{delete result['q'+index];result[question]=values[index]??previous[question]??'';});
  return result;
}
