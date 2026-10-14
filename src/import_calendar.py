"""Import strict des exports ponctuels MyDevinci, sans synchronisation distante."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def parse_calendar(raw):
    text = raw.decode('utf-8-sig')
    lines = re.sub(r'\r?\n[ \t]', '', text).splitlines()
    if not lines or lines[0] != 'BEGIN:VCALENDAR' or lines[-1] != 'END:VCALENDAR':
        raise ValueError('Fichier iCalendar incomplet ou invalide')
    events, fields, warnings = [], None, []
    calendar_zone = 'Europe/Paris'
    def unescape(value):
        return re.sub(r'\\([nN,;\\])', lambda m: '\n' if m[1] in 'nN' else m[1], value)
    def stamp(field):
        params, value = field
        if len(value) == 8:
            return datetime.strptime(value, '%Y%m%d').replace(tzinfo=ZoneInfo(calendar_zone)), True
        zone = timezone.utc if value.endswith('Z') else ZoneInfo(params.get('TZID', calendar_zone).strip('"'))
        return datetime.strptime(value.rstrip('Z'), '%Y%m%dT%H%M%S').replace(tzinfo=zone), False
    for line in lines:
        if line == 'BEGIN:VEVENT':
            if fields is not None: raise ValueError('Événements imbriqués')
            fields = {}
        elif line == 'END:VEVENT':
            if fields is None: raise ValueError('Fin inattendue')
            if any(k in fields for k in ['RRULE', 'RDATE', 'EXDATE', 'RECURRENCE-ID']):
                raise ValueError('Récurrences non prises en charge : export ponctuel nécessaire')
            start, all_day = stamp(fields['DTSTART'])
            end = stamp(fields['DTEND'])[0] if 'DTEND' in fields else start + timedelta(days=1) if all_day else None
            if end is None or end <= start: raise ValueError('Fin de cours absente ou antérieure au début')
            if fields.get('STATUS', ({}, ''))[1] != 'CANCELLED':
                get = lambda key: unescape(fields.get(key, ({}, ''))[1])
                events.append(dict(uid=get('UID'), title=get('SUMMARY'), location=get('LOCATION'), description=get('DESCRIPTION'), start=start.astimezone(ZoneInfo('Europe/Paris')).isoformat(), end=end.astimezone(ZoneInfo('Europe/Paris')).isoformat(), all_day=all_day))
            fields = None
        elif ':' in line:
            header, value = line.split(':', 1)
            parts = header.split(';'); key = parts[0].upper()
            if fields is not None:
                fields[key] = ({p.split('=', 1)[0].upper(): p.split('=', 1)[1] for p in parts[1:] if '=' in p}, value)
            elif key == 'X-WR-TIMEZONE': calendar_zone = value
    if fields is not None: raise ValueError('Événement incomplet')
    if not events: raise ValueError('Aucun événement actif ; ancien calendrier conservé')
    unique = {json.dumps(e, sort_keys=True): e for e in events}
    events = sorted(unique.values(), key=lambda e: (e['start'], e['title']))
    if len({e['uid'] for e in events}) < len(events):
        warnings.append('Certains UID sont réutilisés : les événements distincts sont conservés pour vérification.')
    return dict(events=events, timezone='Europe/Paris', warnings=warnings, source_timezone=calendar_zone)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('file', type=Path)
    p.add_argument('--output', type=Path, default=Path(__file__).resolve().parent.parent/'data/calendar')
    args = p.parse_args()
    raw = args.file.read_bytes()
    if len(raw) > 20_000_000: raise ValueError('Fichier trop volumineux')
    result = parse_calendar(raw)
    digest = hashlib.sha256(raw).hexdigest()
    result.update(source_sha256=digest, imported_utc=datetime.now(timezone.utc).isoformat(), automatic_sync=False)
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output/'sources'; archive.mkdir(exist_ok=True)
    (archive/(digest+'.ics')).write_bytes(raw)
    temp = args.output/'current.tmp'
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(args.output/'current.json')
    print(f"Calendrier importé : {len(result['events'])} événements. Reconstruire l'application pour l'afficher.")


if __name__ == '__main__': main()
