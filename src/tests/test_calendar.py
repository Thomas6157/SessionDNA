import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from import_calendar import parse_calendar

def wrap(*events):
    return ('BEGIN:VCALENDAR\nX-WR-TIMEZONE:Europe/Paris\n'+''.join('BEGIN:VEVENT\n'+e+'\nEND:VEVENT\n' for e in events)+'END:VCALENDAR\n').encode()

EVENT='UID:a\nSUMMARY:Cours\\, DIA\nDTSTART:20260928T081500\nDTEND:20260928T094500'

class CalendarTests(unittest.TestCase):
    def test_local_and_dedup(self):
        r=parse_calendar(wrap(EVENT,EVENT));self.assertEqual(len(r['events']),1)
        self.assertEqual(r['events'][0]['start'],'2026-09-28T08:15:00+02:00')
        self.assertEqual(r['events'][0]['title'],'Cours, DIA')
    def test_winter_utc_and_fold(self):
        r=parse_calendar(wrap('UID:b\nSUMMARY:Long\n  cours\nDTSTART:20261201T070000Z\nDTEND:20261201T080000Z'))
        self.assertEqual(r['events'][0]['start'],'2026-12-01T08:00:00+01:00')
        self.assertEqual(r['events'][0]['title'],'Long cours')
    def test_all_day_end_exclusive(self):
        e=parse_calendar(wrap('UID:b\nDTSTART;VALUE=DATE:20260928\nDTEND;VALUE=DATE:20260929'))['events'][0]
        self.assertTrue(e['all_day']);self.assertTrue(e['end'].startswith('2026-09-29T00:00'))
    def test_reject_recurrence_and_bad_end(self):
        for e in [EVENT+'\nRRULE:FREQ=WEEKLY',EVENT.replace('T094500','T074500')]:
            with self.assertRaises(ValueError):parse_calendar(wrap(e))
    def test_same_uid_different_times_preserved(self):
        r=parse_calendar(wrap(EVENT,EVENT.replace('20260928','20260929')))
        self.assertEqual(len(r['events']),2);self.assertTrue(r['warnings'])
    def test_cancelled(self):
        r=parse_calendar(wrap(EVENT,EVENT.replace('UID:a','UID:b')+'\nSTATUS:CANCELLED'))
        self.assertEqual(len(r['events']),1)

if __name__=='__main__':unittest.main()
