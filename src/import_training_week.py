"""Importer une semaine JSON sans remplacer les versions ni modifier les prescriptions."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
from training_week import validate_week

def import_week(source,output):
    raw=source.read_bytes()
    data=json.loads(raw.decode('utf-8-sig'))
    audit=validate_week(data)
    if audit['errors']:raise ValueError('\n'.join(audit['errors']))
    digest=hashlib.sha256(raw).hexdigest()
    folder=output/data['week_start']/digest[:12]
    if folder.exists():
        if (folder/'source.json').read_bytes()!=raw:raise ValueError('Collision de version : import annulé.')
        return folder,False
    folder.mkdir(parents=True)
    (folder/'source.json').write_bytes(raw)
    manifest=dict(schema_version='sessiondna.training_import.v1',week_start=data['week_start'],source_sha256=digest,imported_utc=datetime.now(timezone.utc).isoformat(),session_count=len(data['sessions']),audit=audit)
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return folder,True

def main():
    root=Path(__file__).resolve().parent.parent
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path);p.add_argument('--output',type=Path,default=root/'data/training/weeks');a=p.parse_args()
    folder,created=import_week(a.file,a.output)
    print(('Semaine importée : ' if created else 'Version déjà présente : ')+str(folder))
    print('Reconstruire ensuite l’application : python src/build_triathlon_app.py')

if __name__=='__main__':main()
