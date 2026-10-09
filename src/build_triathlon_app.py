"""Construit une application statique locale, sans envoyer les données à un service."""
from pathlib import Path
import argparse
import json
import shutil
import pandas as pd
import joblib
from PIL import Image, ImageDraw
from training_week import validate_week

def main():
    root=Path(__file__).resolve().parent.parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,default=root/'data/processed/triathlon/catalog.json')
    p.add_argument('--output',type=Path,default=root/'data/processed/triathlon_app')
    p.add_argument('--model-dir',type=Path,default=root/'data/processed/sport_model')
    p.add_argument('--dataset',type=Path,default=root/'data/processed/supervised/dataset.csv')
    p.add_argument('--history',type=Path,default=root/'data/processed')
    p.add_argument('--training-dir',type=Path,default=root/'data/training/weeks')
    a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    data=json.loads(a.catalog.read_text(encoding='utf-8'))
    data['planning_defaults']=json.loads((Path(__file__).parent/'planning_preferences.json').read_text(encoding='utf-8'))
    versions={}
    for manifest_file in a.training_dir.glob('*/*/manifest.json'):
        manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
        source=manifest_file.with_name('source.json')
        import hashlib
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=manifest['source_sha256']:raise ValueError('Programme modifié après import : '+str(source))
        plan=json.loads(raw.decode('utf-8-sig'));audit=validate_week(plan)
        if audit['errors']:raise ValueError('Programme invalide : '+str(source))
        candidate=dict(plan=plan,manifest=manifest)
        previous=versions.get(plan['week_start'])
        if previous is None or manifest['imported_utc']>previous['manifest']['imported_utc']:versions[plan['week_start']]=candidate
    data['training_weeks']=[versions[k] for k in sorted(versions)]
    calendar_file=root/'data/calendar/current.json'
    data['calendar']=json.loads(calendar_file.read_text(encoding='utf-8')) if calendar_file.exists() else None
    metrics=a.model_dir/'metrics.json'
    data['model_metrics']=json.loads(metrics.read_text(encoding='utf-8')) if metrics.exists() else None
    historical={}
    for folder in ['detection_pauses','test_20/detection']:
        csv=a.history/folder/'comparison.csv'
        if csv.exists():
            for row in pd.read_csv(csv).to_dict('records'):
                historical[row['filename']]={k:None if pd.isna(row.get(k)) else row.get(k) for k in ['n_pauses','pause_s','n_v2','status']}
    for activity in data['activities']:
        activity['historical_detection']=historical.get(activity['filename'])
    form=a.dataset.parent/'annotation.html'
    data['has_annotation_form']=form.exists()
    if form.exists():shutil.copyfile(form,a.output/'annotation.html')
    labels=a.dataset.parent/'annotations_sport.json'
    data['has_annotation_export']=labels.exists()
    if labels.exists():shutil.copyfile(labels,a.output/'annotations_sport.json')
    # Prédictions sur les mêmes variables que l'apprentissage, sans les recalculer autrement.
    if (a.model_dir/'model.joblib').exists() and a.dataset.exists():
        bundle=joblib.load(a.model_dir/'model.joblib')
        dataset=pd.read_csv(a.dataset)
        predictions=bundle['model'].predict(dataset[bundle['features']])
        lookup={row.filename:(pred,row.split) for (_,row),pred in zip(dataset.iterrows(),predictions)}
        for activity in data['activities']:
            item=lookup.get(activity['filename'])
            if item and activity['sport']=='running':
                activity['model_prediction']=dict(objective=item[0],split=item[1],experimental=True)
    # JSON externe : pas d'injection de HTML via les noms/annotations.
    (a.output/'data.js').write_text('window.SESSIONDNA='+json.dumps(data,ensure_ascii=False,allow_nan=False)+';',encoding='utf-8')
    for name in ['index.html','app.js','app.css','training.js','training.css','calendar.js','planner.js','calendar.css','sync.js','sw.js','manifest.webmanifest','icon.svg']:
        shutil.copyfile(Path(__file__).parent/'triathlon_web'/name,a.output/name)
    for size in [180,192,512]:
        icon=Image.new('RGB',(size,size),'#132c32'); draw=ImageDraw.Draw(icon)
        points=[(int(x*size/192),int(y*size/192)) for x,y in [(40,130),(75,62),(105,130),(150,62)]]
        draw.line(points,fill='#81d6b9',width=max(1,int(15*size/192)),joint='curve')
        icon.save(a.output/f'icon-{size}.png')
    print('Application :',a.output/'index.html')

if __name__=='__main__': main()
