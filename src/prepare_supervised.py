"""Préparer un lot d'annotation local, sans étiquettes automatiques."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import pandas as pd
from detect_intervals import read_speed


def main():
    project=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=project)
    parser.add_argument('--output',type=Path,default=None)
    parser.add_argument('--template',type=Path,default=Path(__file__).with_name('annotation_template.html'))
    args=parser.parse_args(); project=args.project
    output=args.output or project/'data/processed/supervised'
    if output.exists(): raise ValueError('Dossier déjà présent : ne pas modifier le lot ni les séparations en cours d’annotation.')
    rows=[]; sessions=[]; sources=[]
    for folder in [project/'data/processed/batch',project/'data/processed/test_20/batch']:
        table=pd.read_csv(folder/'running_features.csv')
        for row in table.to_dict('records'):
            path=project/'data/raw'/row['filename']; speed,_=read_speed(path)
            # Tendance descriptive basée seulement sur les mesures, sans programme Garmin.
            valid=speed.loc[speed.gt(5)].dropna()
            third=max(1,len(valid)//3)
            row['speed_late_early_ratio']=valid.iloc[-third:].median()/valid.iloc[:third].median() if len(valid)>=30 else float('nan')
            row['fit_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            image=folder/'activity_profiles'/(Path(row['filename']).stem+'.png')
            if not image.exists(): raise ValueError(f'Graphique absent : {image}')
            row['split_rank']=hashlib.sha256(('SessionDNA-classification-v1:'+row['filename']).encode()).hexdigest()
            rows.append(row)
            sessions.append(dict(filename=row['filename'],date=pd.to_datetime(row['start_utc'],utc=True).tz_convert('Europe/Paris').strftime('%d/%m/%Y %H:%M'),
                duration=round(row['timer_min'],1),distance=round(row['distance_km'],2),
                image='data:image/png;base64,'+base64.b64encode(image.read_bytes()).decode()))
            sources.append(dict(filename=row['filename'],sha256=row['fit_sha256']))
            print('Préparation :',row['filename'],flush=True)
    data=pd.DataFrame(rows)
    if data.filename.duplicated().any() or data.fit_sha256.duplicated().any() or data.start_utc.duplicated().any(): raise ValueError('Doublons : examiner avant préparation.')
    # Séparation fixe avant labels ; les dates et identifiants ne sont pas des entrées du modèle.
    test=set(data.sort_values('split_rank').head(max(1,round(len(data)*.25))).filename)
    data['split']=data.filename.map(lambda f:'test' if f in test else 'train')
    data=data.sort_values('start_utc').drop(columns='split_rank')
    output.mkdir(parents=True)
    data.to_csv(output/'dataset.csv',index=False)
    digest=hashlib.sha256((output/'dataset.csv').read_bytes()).hexdigest()
    manifest=dict(dataset_id='sessiondna-supervised-'+digest[:16],dataset_sha256=digest,files=sources,
        train_sessions=int(data.split.eq('train').sum()),test_sessions=int(data.split.eq('test').sum()),
        split='25 % des séances par hash fixe avant annotations ; pas de redistribution selon les résultats.',
        limitation='Les 73 courses ont déjà été explorées pour le détecteur. Cette séparation sert un premier essai supervisé, pas une évaluation finale prospective.')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    ordered={s['filename']:s for s in sessions}
    payload=dict(dataset_id=manifest['dataset_id'],sessions=[ordered[f] for f in data.filename])
    template=args.template.read_text(encoding='utf-8')
    (output/'annotation.html').write_text(template.replace('__DATA__',json.dumps(payload,ensure_ascii=False).replace('<','\\u003c')),encoding='utf-8')
    (output/'annotations_sport_template.json').write_text(json.dumps(dict(schema_version=2,taxonomy='sport-v2',dataset_id=manifest['dataset_id'],annotations=[dict(filename=f,objective='',format='',tags={k:'' for k in ['sortie_longue','brick_run','cotes']},notes='',legacy_label='') for f in data.filename]),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Lot prêt :',len(data),'séances ;',manifest['train_sessions'],'apprentissage ;',manifest['test_sessions'],'test exploratoire.')


if __name__=='__main__': main()
