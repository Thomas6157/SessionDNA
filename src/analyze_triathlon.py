"""Inventaire multisport et contexte vélo-course, sans diagnostic physiologique."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import warnings
import fitdecode
import numpy as np
import pandas as pd

SESSION_FIELDS=['sport','sub_sport','start_time','total_elapsed_time','total_timer_time','total_distance','total_ascent','avg_heart_rate','max_heart_rate','avg_power','max_power','avg_cadence','pool_length','num_active_lengths','total_cycles']
LENGTH_FIELDS=['start_time','timestamp','length_type','total_timer_time','total_elapsed_time','total_strokes','swim_stroke']
RECORD_FIELDS=['timestamp','heart_rate','power','cadence','enhanced_speed','speed']


def number(value):
    try:
        x=float(value)
        return x if np.isfinite(x) else None
    except (TypeError,ValueError): return None


def read_fit(path):
    sessions,records,lengths,events=[],[],[],[]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        with fitdecode.FitReader(path) as fit:
            for msg in fit:
                if not isinstance(msg,fitdecode.FitDataMessage): continue
                if msg.name=='session': sessions.append({k:msg.get_value(k,fallback=None) for k in SESSION_FIELDS})
                elif msg.name=='record': records.append({k:msg.get_value(k,fallback=None) for k in RECORD_FIELDS})
                elif msg.name=='length': lengths.append({k:msg.get_value(k,fallback=None) for k in LENGTH_FIELDS})
                elif msg.name=='event' and msg.get_value('event',fallback=None)=='timer': events.append(dict(timestamp=msg.get_value('timestamp',fallback=None),kind=msg.get_value('event_type',fallback=None)))
    return sessions,pd.DataFrame(records,columns=RECORD_FIELDS),pd.DataFrame(lengths,columns=LENGTH_FIELDS),events,len(caught)


def summarize(path):
    sessions,records,lengths,events,warnings_count=read_fit(path)
    if not sessions: raise ValueError('Aucune session FIT.')
    records.timestamp=pd.to_datetime(records.timestamp,utc=True,errors='coerce')
    lengths.start_time=pd.to_datetime(lengths.start_time,utc=True,errors='coerce')
    rows=[]; profiles={}; swim_rows=[]
    for index,s in enumerate(sessions):
        start=pd.to_datetime(s['start_time'],utc=True,errors='coerce')
        elapsed,timer=number(s['total_elapsed_time']),number(s['total_timer_time'])
        if pd.isna(start) or elapsed is None or elapsed<0: raise ValueError('Début/durée de session invalide.')
        end=start+pd.Timedelta(seconds=elapsed)
        mask=records.timestamp.ge(start) & records.timestamp.le(end)
        if index+1<len(sessions):
            next_start=pd.to_datetime(sessions[index+1]['start_time'],utc=True,errors='coerce')
            if pd.notna(next_start): mask &= records.timestamp.lt(next_start)
        r=records.loc[mask].copy()
        l=lengths.copy() if len(sessions)==1 else lengths.loc[lengths.start_time.ge(start) & lengths.start_time.lt(end)].copy()
        key=path.stem+f'_s{index+1}'
        issues=[]
        if records.timestamp.isna().any(): issues.append('points sans horodatage exclus')
        if warnings_count: issues.append(f'{warnings_count} avertissements de décodage')
        if timer is None or timer<=0: issues.append('durée chronométrée absente ou nulle')
        if timer is not None and timer>elapsed:
            issues.append('arrondi durée ≤ 2 s' if timer-elapsed<=2 else 'durées incohérentes > 2 s')
        if r.timestamp.duplicated().any() or not r.timestamp.is_monotonic_increasing: issues.append('horodatages répétés ou désordonnés')
        row=dict(id=key,filename=path.name,session_index=index+1,sport=s['sport'] or 'unknown',sub_sport=s['sub_sport'],start_utc=start.isoformat(),end_utc=end.isoformat(),
            timer_min=timer/60 if timer is not None else None,elapsed_min=elapsed/60,distance_km=(number(s['total_distance']) or 0)/1000 if s['total_distance'] is not None else None,
            duration_delta_s=elapsed-timer if timer is not None else None,ascent_m=number(s['total_ascent']),n_records=len(r),
            hr_session_mean=number(s['avg_heart_rate']),power_session_mean=number(s['avg_power']),cadence_session_mean=number(s['avg_cadence']))
        r['speed_kmh']=pd.to_numeric(r.enhanced_speed.combine_first(r.speed),errors='coerce')*3.6
        for field,prefix in [('speed_kmh','speed'),('heart_rate','hr'),('power','power'),('cadence','cadence')]:
            vals=pd.to_numeric(r[field],errors='coerce'); vals=vals.where(np.isfinite(vals) & vals.ge(0))
            if prefix=='hr': vals=vals.where(vals.gt(0))
            r[field]=vals
            row[prefix+'_mean']=number(vals.mean()); row[prefix+'_std']=number(vals.std()); row[prefix+'_missing_pct']=float(vals.isna().mean()*100) if len(vals) else 100.
        row['speed_cv']=row['speed_std']/row['speed_mean'] if row['speed_mean'] and row['speed_std'] is not None else None
        moving=r.speed_kmh.loc[r.speed_kmh.gt(5)]; third=max(1,len(moving)//3)
        row['speed_late_early_ratio']=number(moving.iloc[-third:].median()/moving.iloc[:third].median()) if len(moving)>=30 else None
        active=l.loc[l.length_type.eq('active')]
        pool=number(s['pool_length'])
        if s['sport']=='swimming':
            row['pool_length_m']=pool; row['active_lengths']=len(active)
            row['rest_lengths']=int(l.length_type.eq('idle').sum())
            row['length_distance_m']=pool*len(active) if pool is not None and len(active) else None
            times=pd.to_numeric(active.total_timer_time,errors='coerce')
            row['length_active_time_s']=number(times.sum(min_count=1))
            row['pace_active_100m_s']=row['length_active_time_s']/row['length_distance_m']*100 if row['length_distance_m'] and row['length_active_time_s'] is not None else None
            row['strokes_per_length']=number(pd.to_numeric(active.total_strokes,errors='coerce').mean())
            row['stroke_types']={str(k):int(v) for k,v in active.swim_stroke.dropna().value_counts().items()}
            if row['length_distance_m'] is not None and row['distance_km'] is not None and abs(row['length_distance_m']-row['distance_km']*1000)>.1:
                issues.append('distance des longueurs différente du résumé : éducatifs/corrections possibles')
            for length_no,item in enumerate(l.to_dict('records')):
                item={k:None if pd.isna(v) else v.isoformat() if isinstance(v,pd.Timestamp) else v for k,v in item.items()}
                swim_rows.append(dict(activity_id=key,length_index=length_no+1,**item))
        # Courbes compactes par tranches de 15 s ; trous conservés, pas d'interpolation.
        points=[]
        if len(r) and not r.timestamp.duplicated().any():
            view=r.set_index('timestamp')[['speed_kmh','heart_rate','power','cadence']].resample('15s').mean()
            for stamp,point in view.iterrows():
                points.append([(stamp-start).total_seconds()/60,*[number(point[k]) for k in view.columns]])
        profiles[key]=points
        row['issues']=issues; row['status']='review' if any('incohérentes' in x or 'horodatages' in x or 'absente ou nulle' in x for x in issues) else 'ok'
        rows.append(row)
    return rows,profiles,swim_rows


def link_bricks(rows,max_gap_min=30):
    bikes=[r for r in rows if r['sport']=='cycling' and r['status']=='ok']
    links=[]
    for run in [r for r in rows if r['sport']=='running' and r['status']=='ok']:
        start=pd.Timestamp(run['start_utc'])
        candidates=[]
        for bike in bikes:
            gap=(start-pd.Timestamp(bike['end_utc'])).total_seconds()/60
            if 0<=gap<=max_gap_min: candidates.append((gap,bike))
        candidates.sort(key=lambda x:x[0])
        if candidates:
            gap,bike=candidates[0]
            links.append(dict(run_id=run['id'],run_filename=run['filename'],bike_id=bike['id'],bike_filename=bike['filename'],transition_min=gap,bike_timer_min=bike['timer_min'],bike_power_mean=bike['power_session_mean'],candidate_count=len(candidates),status='candidate_temporal'))
    return links


def main():
    project=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,default=project/'data/raw'); parser.add_argument('--output',type=Path,default=project/'data/processed/triathlon')
    parser.add_argument('--labels',type=Path,default=project/'data/processed/supervised/annotations_sport.json')
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    cache=args.output/'cache'; cache.mkdir(exist_ok=True)
    rows=[]; curves={}; swim=[]; errors=[]; seen=set(); sources=[]
    for path in sorted(args.raw.glob('*.fit')):
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        sources.append(dict(filename=path.name,sha256=digest))
        if digest in seen: errors.append(dict(filename=path.name,error='Doublon exact exclu')); continue
        seen.add(digest)
        cached=cache/(digest+'.json')
        try:
            entry=json.loads(cached.read_text(encoding='utf-8')) if cached.exists() else None
            if not entry or entry.get('version')!=2 or entry.get('filename')!=path.name:
                print('Analyse :',path.name,flush=True)
                a,p,l=summarize(path)
                entry=dict(version=2,filename=path.name,rows=a,curves=p,lengths=l)
                cached.write_text(json.dumps(entry,ensure_ascii=False,default=str,allow_nan=False),encoding='utf-8')
            rows.extend(entry['rows']); curves.update(entry['curves']); swim.extend(entry['lengths'])
        except Exception as exc: errors.append(dict(filename=path.name,error=f'{type(exc).__name__}: {exc}'))
    # Écarter les doublons probables d'une même session exportée deux fois.
    unique=[]; keys=set()
    for row in rows:
        identity=(row['sport'],row['start_utc'])
        if identity in keys: errors.append(dict(filename=row['filename'],error='Même sport/début déjà présent : session exclue')); continue
        keys.add(identity); unique.append(row)
    rows=sorted(unique,key=lambda r:r['start_utc']); links=link_bricks(rows)
    annotations={}
    if args.labels.exists():
        for a in json.loads(args.labels.read_text(encoding='utf-8-sig')).get('annotations',[]): annotations[a['filename']]=a
    by_run={link['run_id']:link for link in links}
    review=[]
    for row in rows:
        a=annotations.get(row['filename'],{})
        row['human_objective']=a.get('objective',''); row['human_format']=a.get('format',''); row['human_tags']=a.get('tags',{})
        if row['sport']=='running':
            link=by_run.get(row['id']); tag=a.get('tags',{}).get('brick_run','')
            row['brick_candidate']=link
            if tag or link:
                review.append(dict(filename=row['filename'],human_brick=tag,temporal_candidate=bool(link),transition_min=link['transition_min'] if link else None,
                    interpretation='accord' if (tag=='oui' and link) or (tag=='non' and not link) else 'à examiner'))
    pd.DataFrame(rows).to_csv(args.output/'inventory.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(links,columns=['run_id','run_filename','bike_id','bike_filename','transition_min','bike_timer_min','bike_power_mean','candidate_count','status']).to_csv(args.output/'brick_candidates.csv',index=False)
    pd.DataFrame(review).to_csv(args.output/'brick_review.csv',index=False)
    pd.DataFrame(swim).to_csv(args.output/'swim_lengths.csv',index=False)
    pd.DataFrame(errors,columns=['filename','error']).to_csv(args.output/'errors.csv',index=False)
    weeks={}
    for row in rows:
        d=pd.Timestamp(row['start_utc']).tz_convert('Europe/Paris'); monday=(d-pd.Timedelta(days=d.weekday())).strftime('%Y-%m-%d'); key=(monday,row['sport'])
        item=weeks.setdefault(key,dict(week=monday,sport=row['sport'],sessions=0,timer_min=0.,distance_km=0.))
        item['sessions']+=1; item['timer_min']+=row['timer_min'] or 0; item['distance_km']+=row['distance_km'] or 0
    counts=pd.Series([r['sport'] for r in rows]).value_counts().to_dict()
    quality=dict(review=sum(r['status']=='review' for r in rows),with_notes=sum(bool(r['issues']) for r in rows))
    catalog=dict(schema_version=1,generated_utc=datetime.now(timezone.utc).isoformat(),activities=rows,profiles=curves,weeks=list(weeks.values()),counts=counts,errors=errors)
    catalog['quality']=quality
    (args.output/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    (args.output/'manifest.json').write_text(json.dumps(dict(sources=sources,brick_gap_max_min=30,notes='Liens temporels candidats, pas preuve d’enchaînement ; absence de lien ne signifie pas absence de brick. Statistiques capteurs par point présent ; courbes regroupées par 15 s.'),ensure_ascii=False,indent=2),encoding='utf-8')
    text=['# SessionDNA — Inventaire triathlon','',f'{len(rows)} sessions ; sports : {counts}. {len(errors)} fichiers/sessions en erreur ou exclus. {quality["review"]} sessions à revoir ; {quality["with_notes"]} avec remarques. {len(links)} liens vélo-course candidats.','',
        'Les sessions multisport sont séparées. Le vélo est relié à la course si sa fin précède le départ de 0 à 30 minutes ; cette règle est un indice de contexte à confirmer, pas une déduction depuis la fréquence cardiaque.', '',
        'La natation en piscine utilise les messages length lorsqu’ils existent. La distance officielle reste celle de session ; distance et allure issues des longueurs sont indiquées séparément. En eau libre ou sans longueurs, ces métriques restent absentes.', '',
        'Les écarts de durée ≤ 2 secondes sont signalés comme arrondis possibles ; les écarts supérieurs passent en revue. Aucun FIT n’est corrigé. Les moyennes des points ne sont pas pondérées par le temps. Les graphiques utilisent des moyennes par 15 secondes.', '',
        'Fichiers : inventory.csv, brick_candidates.csv, brick_review.csv, swim_lengths.csv, errors.csv, catalog.json et manifest.json.', '',
        'Les comptes rendus restent descriptifs. Aucun diagnostic de fatigue, de blessure ni prescription d’entraînement ne découle automatiquement des données.', '',
        'Sources : [structure FIT](https://developer.garmin.com/fit/articles/file-types/activity.html), [natation FIT](https://developer.garmin.com/fit/articles/cookbook/decoding_activity_files.html).']
    (args.output/'report.md').write_text('\n'.join(text),encoding='utf-8')
    print(counts, 'erreurs/signaux :',len(errors), 'liens :',len(links))


if __name__=='__main__': main()
