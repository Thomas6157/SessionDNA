"""Premier modèle exploratoire sur objectifs sportifs humains, séparation existante conservée."""
from pathlib import Path
import argparse
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold,cross_val_score
from sklearn.metrics import classification_report,confusion_matrix
from sports_labels import validate_sports

FEATURES=['timer_min','speed_mean','speed_cv','speed_late_early_ratio','hr_mean','hr_std']
CLASSES=['ef','endurance_soutenue','seuil']

def main():
    project=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=project/'data/processed/supervised')
    parser.add_argument('--labels',type=Path,default=project/'data/processed/supervised/annotations_sport.json')
    parser.add_argument('--output',type=Path,default=project/'data/processed/sport_model')
    args=parser.parse_args()
    if args.output.exists(): raise ValueError('Choisir un dossier inédit ; ne pas écraser le premier test.')
    manifest=json.loads((args.dataset/'manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((args.dataset/'dataset.csv').read_bytes()).hexdigest()==manifest['dataset_sha256']
    data=pd.read_csv(args.dataset/'dataset.csv')
    payload=json.loads(args.labels.read_text(encoding='utf-8-sig'))
    annotations=pd.DataFrame(validate_sports(payload,manifest['dataset_id'],set(data.filename)))
    data=data.merge(annotations[['filename','objective']],on='filename',validate='one_to_one')
    accepted=data.loc[data.objective.isin(CLASSES)].copy()
    train=accepted.loc[accepted.split.eq('train')]; test=accepted.loc[accepted.split.eq('test')]
    counts=pd.crosstab(accepted.objective,accepted.split).reindex(CLASSES,fill_value=0)
    if (counts.get('train',pd.Series(0,index=CLASSES))<3).any() or (counts.get('test',pd.Series(0,index=CLASSES))<1).any():
        raise ValueError('Essai exploratoire : au moins 3 exemples train et 1 test par classe requis. Aucun déplacement de séance entre lots.')
    models={
        'majoritaire':make_pipeline(SimpleImputer(strategy='median'),DummyClassifier(strategy='most_frequent')),
        'logistique':make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(max_iter=3000,class_weight='balanced',random_state=42)),
        'foret':make_pipeline(SimpleImputer(strategy='median'),RandomForestClassifier(n_estimators=200,max_depth=4,min_samples_leaf=2,class_weight='balanced',random_state=42,n_jobs=1))}
    scores=[]; cv=StratifiedKFold(n_splits=3,shuffle=True,random_state=42)
    for name,model in models.items():
        values=cross_val_score(model,train[FEATURES],train.objective,cv=cv,scoring='f1_macro',error_score='raise')
        scores.append(dict(model=name,mean=float(values.mean()),std=float(values.std()),folds=values.tolist()))
    chosen=max(scores,key=lambda s:s['mean'])['model']
    model=models[chosen].fit(train[FEATURES],train.objective)
    prediction=model.predict(test[FEATURES])
    metrics=classification_report(test.objective,prediction,labels=CLASSES,output_dict=True,zero_division=0)
    args.output.mkdir(parents=True)
    pd.DataFrame(scores).to_csv(args.output/'validation.csv',index=False)
    counts.to_csv(args.output/'class_counts.csv')
    test[['filename','objective']].assign(prediction=prediction).to_csv(args.output/'test_predictions.csv',index=False)
    pd.DataFrame(confusion_matrix(test.objective,prediction,labels=CLASSES),index=CLASSES,columns=CLASSES).to_csv(args.output/'confusion_matrix.csv')
    # Le modèle sauvegardé reste ajusté uniquement sur train, pour préserver l'expérience.
    joblib.dump(dict(model=model,features=FEATURES,labels=CLASSES,dataset_id=manifest['dataset_id'],target='objective',exploratory=True),args.output/'model.joblib')
    summary=dict(chosen=chosen,train_n=len(train),test_n=len(test),validation=scores,metrics=metrics,features=FEATURES,
        labels_sha256=hashlib.sha256(args.labels.read_bytes()).hexdigest(),dataset_sha256=manifest['dataset_sha256'],
        limitations=['Trois exemples de seuil en apprentissage dans le lot actuel.', 'Même sportif et données déjà explorées ; test non prospectif.', 'Ne reconnaît ni VO2max, ni compétition, ni brick : seulement les trois objectifs retenus.'])
    (args.output/'metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (args.output/'report.md').write_text(f'''# Premier modèle supervisé sportif — exploratoire

{len(train)} séances d'apprentissage, {len(test)} séances de test ; séparation existante conservée. Objectif humain : EF / endurance soutenue / seuil.

Modèle retenu sur validation croisée train : **{chosen}**. F1 macro du petit test : **{metrics['macro avg']['f1-score']:.3f}**. Exactitude : **{metrics['accuracy']:.1%}**.

Le F1 macro donne le même poids à chacune des trois classes. Voir confusion_matrix.csv et test_predictions.csv pour les erreurs. Aucun réglage n'a utilisé les résultats du test.

Cet essai abaisse explicitement le seuil d'effectif du premier protocole v1 pour permettre une démonstration : seulement trois exemples de seuil en apprentissage. C'est une nouvelle expérience exploratoire, pas une validation de production. La variabilité des trois plis est importante à examiner. Aucun bilan médical ni conseil de charge d'entraînement ne découle de ces prédictions.

Les entrées sont six résumés de mesures, sans consigne Garmin, date, nom de séance, ni annotation de brick. Le contexte vélo est analysé séparément. Les autres objectifs restent hors périmètre et ne doivent pas être forcés dans ces trois classes.
''',encoding='utf-8')
    print(json.dumps(dict(chosen=chosen,train=len(train),test=len(test),f1=metrics['macro avg']['f1-score'],accuracy=metrics['accuracy'])))

if __name__=='__main__': main()
