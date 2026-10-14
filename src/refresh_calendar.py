"""Repère un nouvel export MyDevinci dans Téléchargements, sans accéder au portail."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def candidate(downloads, current):
    files=[p for p in downloads.glob('mon_calendrier*.ics') if p.is_file()]
    if not files:return None
    latest=max(files,key=lambda p:p.stat().st_mtime)
    if current.exists():
        saved=json.loads(current.read_text(encoding='utf-8'))
        if hashlib.sha256(latest.read_bytes()).hexdigest()==saved['source_sha256']:return None
        if latest.stat().st_mtime<=datetime.fromisoformat(saved['imported_utc']).timestamp():return None
    return latest


def main():
    root=Path(__file__).resolve().parent.parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--downloads',type=Path,default=Path.home()/'Downloads')
    a=p.parse_args()
    file=candidate(a.downloads,root/'data/calendar/current.json')
    if file:
        subprocess.run([sys.executable,str(root/'src/import_calendar.py'),str(file)],check=True)
    else:print('Calendrier : aucun nouvel export détecté.')

if __name__=='__main__':main()
