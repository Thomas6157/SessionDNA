"""Tests techniques sur données entièrement synthétiques, sans résultat sportif."""
from pathlib import Path
import sys
import tempfile
import subprocess
import hashlib
import json
import numpy as np
import pandas as pd
module_dir=next(parent for parent in Path(__file__).resolve().parents if (parent/'train_classifier.py').is_file())
sys.path.insert(0,str(module_dir))
from train_classifier import LABELS, FEATURES, load_annotations, blockers

with tempfile.TemporaryDirectory() as name:
    root=Path(name); rows=[]; annotations=[]
    rng=np.random.default_rng(13)
    for c,label in enumerate(LABELS):
        for i in range(12):
            f=f'{label}_{i}.fit'
            rows.append(dict(filename=f,split='train' if i<9 else 'test',**{k:float(c*8+rng.normal()) for k in FEATURES}))
            annotations.append(dict(filename=f,label=label))
    data=pd.DataFrame(rows); data.to_csv(root/'dataset.csv',index=False)
    manifest=dict(dataset_id='SYNTHETIC_TEST_ONLY',dataset_sha256=hashlib.sha256((root/'dataset.csv').read_bytes()).hexdigest())
    (root/'manifest.json').write_text(json.dumps(manifest))
    labels=root/'labels.json'; labels.write_text(json.dumps(dict(dataset_id=manifest['dataset_id'],annotations=annotations)))
    table=load_annotations(data,labels,manifest['dataset_id']); assert not blockers(table)
    assert blockers(data.assign(label=''))
    bad=dict(dataset_id=manifest['dataset_id'],annotations=annotations+[annotations[0]])
    labels.write_text(json.dumps(bad))
    try: load_annotations(data,labels,manifest['dataset_id'])
    except ValueError: pass
    else: raise AssertionError('Duplicate labels accepted')
    labels.write_text(json.dumps(dict(dataset_id=manifest['dataset_id'],annotations=annotations)))
    script=module_dir/'train_classifier.py'
    subprocess.run([sys.executable,'-B',str(script),'--dataset',str(root),'--labels',str(labels),'--output',str(root/'result')],check=True)
    metrics=json.loads((root/'result/metrics.json').read_text())
    assert metrics['train_sessions']==27 and metrics['test_sessions']==9
    assert (root/'result/model.joblib').is_file()
    assert len(pd.read_csv(root/'result/test_predictions.csv'))==9
print('PASS : vérification labels, doublons, garde-fous, pipeline complet sur données synthétiques uniquement.')
