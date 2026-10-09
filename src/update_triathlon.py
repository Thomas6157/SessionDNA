"""Actualise les analyses et l'application ; --sync importe Garmin au préalable."""
from pathlib import Path
import argparse
import subprocess
import sys
import os

def main():
    root=Path(__file__).resolve().parent.parent
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sync',action='store_true')
    p.add_argument('--calendar-downloads',action='store_true',help='Importer un export MyDevinci plus récent trouvé dans Téléchargements')
    a=p.parse_args()
    scripts=[]
    if a.sync:scripts.append(['sync_garmin.py','--sport','all'])
    if a.calendar_downloads:scripts.append(['refresh_calendar.py'])
    scripts.extend([['analyze_triathlon.py'],['build_triathlon_app.py']])
    if (root/'src/build_analytics.py').exists():scripts.append(['build_analytics.py'])
    state=root/'data/sync';state.mkdir(parents=True,exist_ok=True)
    lock=state/'update.lock'
    try:
        with lock.open('x',encoding='utf-8') as stream:stream.write(str(os.getpid()))
    except FileExistsError:
        p.error('Une actualisation est en cours, ou update.lock subsiste après une interruption. Vérifier le processus avant de retirer ce fichier.')
    try:
        for script,*args in scripts:subprocess.run([sys.executable,'-B',str(root/'src'/script),*args],cwd=root,check=True)
    finally:lock.unlink(missing_ok=True)

if __name__=='__main__': main()
