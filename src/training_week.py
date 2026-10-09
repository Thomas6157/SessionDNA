"""Validation structurelle d'un programme fourni ; aucune prescription n'est modifiée."""
from datetime import date, timedelta
import math
import re

SCHEMA='sessiondna.training_week.v1'
SPORTS={'running','cycling','swimming','strength','mobility','other'}

def validate_week(data):
    errors=[]; notes=[]; summaries=[]
    def fail(path,msg):errors.append(f'{path} : {msg}')
    def number(v,path,positive=False):
        if v is None:return
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or (positive and v==0):fail(path,'nombre positif attendu' if positive else 'nombre fini ≥ 0 attendu')
    def strings(v,path):
        if not isinstance(v,list) or not all(isinstance(x,str) for x in v):fail(path,'liste de textes attendue')
    def interval(v,path,rpe=False):
        if v is None:return
        if not isinstance(v,dict):fail(path,'objet min/max ou null attendu');return
        for k in ('min','max'):
            number(v.get(k),path+'.'+k)
            if rpe and isinstance(v.get(k),(int,float)) and v[k]>10:fail(path,'RPE hors échelle 0–10')
        lo,hi=v.get('min'),v.get('max')
        if isinstance(lo,(int,float)) and isinstance(hi,(int,float)) and lo>hi:fail(path,'min supérieur à max')
    if not isinstance(data,dict):return {'errors':['Objet JSON attendu.'],'notes':[],'sessions':[]}
    if data.get('schema_version')!=SCHEMA:fail('schema_version','version non prise en charge')
    try:
        start=date.fromisoformat(data['week_start'])
        if start.weekday()!=0:fail('week_start','un lundi est attendu')
    except (KeyError,TypeError,ValueError):fail('week_start','date ISO invalide');start=None
    if data.get('timezone')!='Europe/Paris':fail('timezone','Europe/Paris attendu pour cette version')
    sessions=data.get('sessions')
    if not isinstance(sessions,list) or not sessions:return {'errors':errors+['sessions : liste non vide attendue'],'notes':notes,'sessions':[]}
    ids=[]
    for i,s in enumerate(sessions):
        path=f'sessions[{i}]'
        if not isinstance(s,dict):fail(path,'objet attendu');continue
        sid=s.get('id');ids.append(sid)
        if not isinstance(sid,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',sid):fail(path+'.id','identifiant invalide')
        try:
            day=date.fromisoformat(s['date'])
            if start and not start<=day<start+timedelta(days=7):fail(path+'.date','hors de la semaine')
        except (KeyError,TypeError,ValueError):fail(path+'.date','date ISO invalide')
        if s.get('sport') not in SPORTS:fail(path+'.sport','sport inconnu')
        for k in ('title','objective'):
            if not isinstance(s.get(k),str) or not s[k].strip():fail(path+'.'+k,'texte non vide attendu')
        for k in ('equipment','execution_notes','adjustment_options','feedback_questions'):strings(s.get(k,[]),path+'.'+k)
        number(s.get('planned_duration_min'),path+'.planned_duration_min',True)
        number(s.get('planned_distance_m'),path+'.planned_distance_m',True)
        interval(s.get('target_session_rpe'),path+'.target_session_rpe',True)
        if isinstance(s.get('target_session_rpe'),dict) and s['target_session_rpe'].get('scale','0-10')!='0-10':fail(path+'.target_session_rpe.scale','0-10 attendu')
        blocks=s.get('blocks');seconds=meters=0.;all_time=all_distance=True;local_notes=[]
        if not isinstance(blocks,list) or not blocks:fail(path+'.blocks','liste non vide attendue');blocks=[]
        for j,b in enumerate(blocks):
            bp=f'{path}.blocks[{j}]'
            if not isinstance(b,dict):fail(bp,'objet attendu');continue
            repeat=b.get('repeat')
            if type(repeat) is not int or not 1<=repeat<=1000:fail(bp+'.repeat','entier de 1 à 1000 attendu');repeat=1
            if not isinstance(b.get('name'),str):fail(bp+'.name','texte attendu')
            steps=b.get('steps')
            if not isinstance(steps,list) or not steps:fail(bp+'.steps','liste non vide attendue');continue
            for k,t in enumerate(steps):
                tp=f'{bp}.steps[{k}]'
                if not isinstance(t,dict):fail(tp,'objet attendu');continue
                if t.get('type') not in {'warmup','work','recovery','cooldown','drill','rest'}:fail(tp+'.type','type inconnu')
                if not isinstance(t.get('instructions',''),str):fail(tp+'.instructions','texte attendu')
                for key in ('duration_sec','distance_m'):number(t.get(key),tp+'.'+key,True)
                for key in ('target_rpe','target_pace_sec_per_km','target_pace_sec_per_100m','target_power_w','target_heart_rate_bpm'):interval(t.get(key),tp+'.'+key,key=='target_rpe')
                dur,dist=t.get('duration_sec'),t.get('distance_m')
                if isinstance(dur,(int,float)) and math.isfinite(dur):seconds+=repeat*dur
                else:all_time=False
                if isinstance(dist,(int,float)) and math.isfinite(dist):meters+=repeat*dist
                elif t.get('type') not in {'rest','recovery'}:all_distance=False
        planned=s.get('planned_duration_min')
        if all_time and isinstance(planned,(int,float)) and abs(seconds/60-planned)>.02:local_notes.append(f'Durée des étapes {seconds/60:.2f} min différente des {planned} min annoncées ; aucune correction automatique.')
        if not all_time:local_notes.append('Durée des étapes partiellement renseignée : le total ne peut pas être contrôlé exactement.')
        distance=s.get('planned_distance_m')
        if all_distance and isinstance(distance,(int,float)) and abs(meters-distance)>.1:local_notes.append(f'Distance des étapes {meters:g} m différente des {distance:g} m annoncés.')
        if s.get('sport')=='swimming':local_notes.append('Vérifier le temps écoulé : le programme peut annoncer le temps de nage actif hors récupérations.')
        schedule=s.get('scheduling')
        if not isinstance(schedule,dict):fail(path+'.scheduling','objet attendu')
        else:
            if type(schedule.get('fixed_date')) is not bool:fail(path+'.scheduling.fixed_date','booléen attendu')
            strings(schedule.get('constraints',[]),path+'.scheduling.constraints')
            preferred=schedule.get('preferred_time')
            if preferred is not None and (not isinstance(preferred,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',preferred)):fail(path+'.scheduling.preferred_time','HH:MM ou null attendu')
            strings(schedule.get('allowed_dates',[]),path+'.scheduling.allowed_dates')
        summaries.append(dict(id=sid,explicit_duration_sec=seconds,explicit_distance_m=meters,all_durations_explicit=all_time,all_distances_explicit=all_distance,notes=local_notes))
        notes.extend(f'{sid} : {n}' for n in local_notes)
    safeids=[x for x in ids if isinstance(x,str)]
    if len(safeids)!=len(set(safeids)):fail('sessions','identifiants dupliqués')
    for s in sessions:
        if isinstance(s,dict) and isinstance(s.get('scheduling'),dict):
            linked=s['scheduling'].get('linked_session_id')
            if linked is not None and (linked not in safeids or linked==s.get('id')):fail(str(s.get('id')),'liaison vers une séance absente ou elle-même')
    for k in ('rest_days','weekly_review_questions','planning_notes'):strings(data.get(k,[]),k)
    return dict(errors=errors,notes=notes,sessions=summaries)
