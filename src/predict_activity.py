"""Appliquer un classifieur local SessionDNA à une nouvelle course FIT."""
from pathlib import Path
import argparse
import json
import joblib
import pandas as pd
from analyze_activities import read_activity, summarize_activity


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True,help='model.joblib créé par train_classifier.py')
    parser.add_argument('--file',type=Path,required=True)
    args=parser.parse_args()
    bundle=joblib.load(args.model)
    sessions,records,warnings=read_activity(args.file)
    row,records=summarize_activity(args.file,sessions,records,warnings)
    if row.get('status')!='ok' or row.get('sport')!='running': raise ValueError('Course non admissible : '+str(row.get('issues','')))
    speed=records.speed_kmh.loc[records.speed_kmh.gt(5)].dropna()
    third=max(1,len(speed)//3)
    row['speed_late_early_ratio']=speed.iloc[-third:].median()/speed.iloc[:third].median() if len(speed)>=30 else float('nan')
    features=pd.DataFrame([row]).reindex(columns=bundle['features'])
    prediction=bundle['model'].predict(features)[0]
    print(json.dumps(dict(filename=args.file.name,proposed_category=prediction,
        note='Catégorie proposée par le modèle ; vérifier le contexte de la séance.'),ensure_ascii=False,indent=2))


if __name__=='__main__': main()
