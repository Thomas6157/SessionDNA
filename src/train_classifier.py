"""Contrôler les annotations puis comparer des classifieurs, sans inventer d'étiquettes."""
from pathlib import Path
import argparse
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LABELS=['reguliere','progressive','intervalles']
FEATURES=['timer_min','speed_mean','speed_cv','speed_late_early_ratio','hr_mean','hr_std']


def load_annotations(dataset, path, dataset_id):
    payload=json.loads(path.read_text(encoding='utf-8-sig'))
    if payload.get('dataset_id')!=dataset_id: raise ValueError('Annotations d’un autre lot : vérifier dataset_id.')
    labels=pd.DataFrame(payload.get('annotations',[]))
    if labels.empty: return dataset.assign(label='')
    if not {'filename','label'}.issubset(labels): raise ValueError('Colonnes filename et label requises.')
    if labels.filename.duplicated().any(): raise ValueError('Annotations dupliquées.')
    if not labels.filename.isin(dataset.filename).all(): raise ValueError('Séance inconnue dans les annotations.')
    if not labels.label.isin(LABELS+['autre','incertain','']).all(): raise ValueError('Catégorie inconnue.')
    return dataset.merge(labels[['filename','label']],on='filename',how='left',validate='one_to_one').fillna({'label':''})


def blockers(table):
    problems=[]
    for split,minimum in [('train',6),('test',2)]:
        counts=table.loc[table.split.eq(split),'label'].value_counts()
        for label in LABELS:
            if counts.get(label,0)<minimum: problems.append(f'{split} : {counts.get(label,0)} {label}, minimum {minimum}.')
    return problems


def main():
    project=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=project/'data/processed/supervised')
    parser.add_argument('--labels',type=Path)
    parser.add_argument('--output',type=Path,default=project/'data/processed/classifier')
    parser.add_argument('--check',action='store_true',help='État des annotations, sans entraînement.')
    args=parser.parse_args()
    data=pd.read_csv(args.dataset/'dataset.csv')
    manifest=json.loads((args.dataset/'manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256((args.dataset/'dataset.csv').read_bytes()).hexdigest()!=manifest['dataset_sha256']: raise ValueError('Dataset modifié depuis sa préparation.')
    if args.labels is None or not args.labels.exists():
        print('En attente : annoter les séances dans annotation.html puis exporter annotations.json.')
        print('Aucun modèle supervisé entraîné.')
        return
    annotation_payload=json.loads(args.labels.read_text(encoding='utf-8-sig'))
    if annotation_payload.get('schema_version')==2:
        from sports_labels import validate_sports, TAGS
        rows=validate_sports(annotation_payload,manifest['dataset_id'],set(data.filename))
        for field in ['objective','format',*TAGS]:
            values=[row.get(field,'') if field in ['objective','format'] else row.get('tags',{}).get(field,'') for row in rows]
            print('\n'+field+' :')
            print(pd.Series(values,dtype='str').replace('','non_renseigne').value_counts().to_string())
        print('\nAnnotations sport v2 contrôlées. Aucun entraînement lancé.')
        print('Choisir la cible et les classes représentées avant d’adapter le modèle. Les tags ne sont pas des classes exclusives.')
        if not args.check:
            print('Utiliser --check pour contrôler cet export. L’ancien entraînement à trois classes est réservé aux annotations v1.')
        return
    data=load_annotations(data,args.labels,manifest['dataset_id'])
    print(pd.crosstab(data.label.replace('','non_annote'),data.split).to_string())
    reasons=blockers(data)
    if reasons:
        print('\nEntraînement non lancé :\n'+'\n'.join(reasons))
        print('Compléter les annotations. Si une classe est réellement rare, revoir le périmètre avec l’utilisateur ; ne pas inventer des exemples.')
        return
    if args.check:
        print('Annotations suffisantes pour un premier essai exploratoire. Aucun entraînement demandé.')
        return
    if args.output.exists(): raise ValueError('Choisir un dossier --output inédit pour préserver la première évaluation.')
    train=data.loc[data.split.eq('train') & data.label.isin(LABELS)].copy()
    test=data.loc[data.split.eq('test') & data.label.isin(LABELS)].copy()
    if np.isinf(data[FEATURES].to_numpy(dtype=float)).any(): raise ValueError('Caractéristiques infinies.')
    if train[FEATURES].isna().all().any(): raise ValueError('Une caractéristique est entièrement absente en apprentissage.')
    models={
        'majoritaire':make_pipeline(SimpleImputer(strategy='median'),DummyClassifier(strategy='most_frequent')),
        'logistique':make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(max_iter=2000,class_weight='balanced',random_state=42)),
        'foret':make_pipeline(SimpleImputer(strategy='median'),RandomForestClassifier(n_estimators=200,max_depth=4,min_samples_leaf=2,class_weight='balanced',random_state=42,n_jobs=1)),
    }
    cv=StratifiedKFold(n_splits=3,shuffle=True,random_state=42)
    results=[]
    for name,model in models.items():
        scores=cross_val_score(model,train[FEATURES],train.label,cv=cv,scoring='f1_macro',error_score='raise')
        results.append(dict(model=name,cv_f1_macro_mean=float(scores.mean()),cv_f1_macro_std=float(scores.std())))
    # Le test n'intervient pas dans le choix du modèle.
    selected=max(results,key=lambda row:row['cv_f1_macro_mean'])['model']
    model=models[selected].fit(train[FEATURES],train.label)
    predictions=model.predict(test[FEATURES])
    report=classification_report(test.label,predictions,labels=LABELS,output_dict=True,zero_division=0)
    args.output.mkdir(parents=True)
    pd.DataFrame(results).to_csv(args.output/'validation.csv',index=False)
    test[['filename','label']].assign(prediction=predictions).to_csv(args.output/'test_predictions.csv',index=False)
    pd.DataFrame(confusion_matrix(test.label,predictions,labels=LABELS),index=LABELS,columns=LABELS).to_csv(args.output/'confusion_matrix.csv')
    joblib.dump(dict(model=model,features=FEATURES,labels=LABELS,dataset_id=manifest['dataset_id']),args.output/'model.joblib')
    metadata=dict(selected_model=selected,train_sessions=len(train),test_sessions=len(test),features=FEATURES,
        classification_report=report,labels_sha256=hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        dataset_sha256=manifest['dataset_sha256'],validation=results,
        limitation='Séparation fixe par séance sur des données déjà explorées ; test exploratoire même sportif, pas validation prospective.')
    (args.output/'metrics.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    (args.output/'report.md').write_text(f'# Premier classifieur supervisé\n\nModèle choisi sur validation : {selected}.\n\n{len(train)} séances d’apprentissage ; {len(test)} séances de test annotées.\n\nF1 macro du test : {report["macro avg"]["f1-score"]:.3f}.\n\nVoir validation.csv, confusion_matrix.csv et test_predictions.csv pour examiner les erreurs.\n\nLes scores ne garantissent pas la fiabilité sur d’autres sportifs. Tout changement fondé sur ce test nécessitera une nouvelle évaluation intacte.\n',encoding='utf-8')
    print('Modèle et bilan enregistrés :',args.output)


if __name__=='__main__': main()
