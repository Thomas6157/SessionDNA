import hashlib
import json
import sys
import tempfile
import threading
import unittest
import io
import zipfile
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sessiondna_api import create_app
from sessiondna_store import SQLiteStateStore


class StoreTests(unittest.TestCase):
    def test_migration_and_compare_and_swap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / 'current.json'
            original = {'revision': 'legacy-revision', 'items': {'sessiondna-planning-v1': {'weeks': {'abc': {'s1': '10:00'}}}}}
            legacy.write_text(json.dumps(original), encoding='utf-8')
            before = legacy.read_bytes()
            store = SQLiteStateStore(root / 'state.sqlite3', legacy)
            self.assertEqual(store.read(), original)
            writes = []
            def writer(number):
                writes.append(store.write('legacy-revision', {'sessiondna-planning-v1': {'number': number}}))
            workers = [threading.Thread(target=writer, args=(n,)) for n in range(2)]
            for t in workers: t.start()
            for t in workers: t.join()
            self.assertEqual(sum(x is not None for x in writes), 1)
            self.assertEqual(legacy.read_bytes(), before)
            self.assertEqual(len(store.history()), 2)
            restored = SQLiteStateStore(store.snapshot(root / 'copy.sqlite3'))
            self.assertEqual(restored.read(), store.read())

    def test_bad_legacy_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / 'current.json'
            legacy.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError):
                SQLiteStateStore(root / 'state.sqlite3', legacy)
            self.assertEqual(legacy.read_text(), '{broken')


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        folder = self.root / 'data/processed/triathlon'
        folder.mkdir(parents=True)
        (folder / 'catalog.json').write_text(json.dumps({'activities': [{'id': 'a_s0', 'filename': 'a.fit', 'sport': 'running', 'start_utc': '2026-09-29T08:00:00Z'}, {'id': 'b_s0', 'sport': 'cycling', 'start_utc': '2026-09-28T08:00:00Z'}], 'profiles': {'a_s0': [[0, 12, 145, None, 80]]}, 'counts': {'running': 1, 'cycling': 1}, 'weeks': []}), encoding='utf-8')
        self.client = TestClient(create_app(self.root), base_url='http://127.0.0.1:8765')
        self.headers = {'Origin': 'http://127.0.0.1:8765'}

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_lightweight_bootstrap_and_detail(self):
        response = self.client.get('/api/bootstrap')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('profiles', response.json())
        self.assertNotIn('activities', response.json())
        listed = self.client.get('/api/activities?sport=running&limit=1').json()
        self.assertEqual(listed['total'], 1)
        self.assertEqual(listed['items'][0]['id'], 'a_s0')
        self.assertEqual(self.client.get('/api/activities/a_s0').json()['profile'][0][1], 12)
        self.assertEqual(self.client.get('/api/activities/absent').status_code, 404)

    def test_origin_state_conflict_and_invalid_space(self):
        initial = self.client.get('/api/state').json()
        payload = {'revision': initial['revision'], 'items': {'sessiondna-journal-v1': {'day': 'note'}}}
        self.assertEqual(self.client.post('/api/state', json=payload).status_code, 403)
        self.assertEqual(self.client.get('/api/state', headers={'Host': 'evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/state', json=payload, headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/state', json=payload, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.post('/api/state', json=payload, headers=self.headers).status_code, 409)
        current = self.client.get('/api/state').json()
        self.assertEqual(self.client.post('/api/state', json={'revision': current['revision'], 'items': {'secret': {}}}, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.get('/api/state').json(), current)

    def test_import_calendar_is_dated_snapshot_and_invalid_does_not_replace(self):
        raw = b'BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:x\r\nDTSTART:20260929T100000Z\r\nDTEND:20260929T110000Z\r\nSUMMARY:Test\r\nEND:VEVENT\r\nEND:VCALENDAR'
        response = self.client.post('/api/import/calendar', files={'file': ('calendar.ics', raw)}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['automatic_sync'])
        snapshot = (self.root / 'data/calendar/current.json').read_bytes()
        bad = self.client.post('/api/import/calendar', files={'file': ('calendar.ics', b'invalid')}, headers=self.headers)
        self.assertEqual(bad.status_code, 400)
        self.assertEqual((self.root / 'data/calendar/current.json').read_bytes(), snapshot)
        archive = self.root / ('data/calendar/sources/' + hashlib.sha256(raw).hexdigest() + '.ics')
        self.assertEqual(archive.read_bytes(), raw)

    def test_program_import_version_immutable_and_duplicates_ignored(self):
        program = {'schema_version': 'sessiondna.training_week.v1', 'week_start': '2026-09-28', 'timezone': 'Europe/Paris', 'sessions': [{'id':'s1','date':'2026-09-28','sport':'running','title':'Test','objective':'EF','planned_duration_min':30,'blocks':[{'name':'EF','repeat':1,'steps':[{'type':'work','duration_sec':1800}]}],'scheduling':{'fixed_date':True}}]}
        raw = json.dumps(program).encode()
        response = self.client.post('/api/import/training', files={'file':('week.json',raw)},headers=self.headers)
        self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(response.json()['created'])
        self.assertFalse(self.client.post('/api/import/training',files={'file':('week.json',raw)},headers=self.headers).json()['created'])
        self.assertEqual(len(self.client.get('/api/bootstrap').json()['training_weeks']),1)
        original = next((self.root/'data/training/weeks').glob('*/*/source.json'))
        self.assertEqual(original.read_bytes(),raw)

    def test_running_pipeline_prevents_second_start(self):
        lock = self.root/'data/sync/update.lock'
        lock.parent.mkdir(parents=True)
        lock.write_text('123')
        response = self.client.post('/api/update',json={'sync':False},headers=self.headers)
        self.assertEqual(response.status_code,409)

    def test_backup_uses_restorable_ui_schema(self):
        response = self.client.get('/api/backup')
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            state = json.loads(archive.read('state.json'))
            self.assertEqual(state['schema_version'], 'sessiondna.backup.v2')
            self.assertEqual(state['items'], self.client.get('/api/state').json()['items'])

    def test_date_filter_uses_paris_not_utc(self):
        path = self.root/'data/processed/triathlon/catalog.json'
        payload = json.loads(path.read_text())
        payload['activities'][0]['start_utc'] = '2026-09-27T22:30:00Z'
        path.write_text(json.dumps(payload))
        response = self.client.get('/api/activities?sport=running&start=2026-09-28&end=2026-09-28')
        self.assertEqual(response.json()['total'], 1)
        self.assertEqual(self.client.get('/api/activities?start=bad').status_code, 400)

    def test_invalid_nested_program_returns_400_without_writing(self):
        program = {'schema_version':'sessiondna.training_week.v1','week_start':'2026-09-28','timezone':'Europe/Paris','sessions':[{'id':'a','sport':[]}]}
        response = self.client.post('/api/import/training',files={'file':('bad.json',json.dumps(program).encode())},headers=self.headers)
        self.assertEqual(response.status_code,400)
        self.assertFalse((self.root/'data/training/weeks').exists())

    def test_fit_crc_validation_and_duplicate_detection(self):
        from fitdecode.utils import compute_crc
        data = struct.pack('<BBBHB', 0x40, 0, 0, 18, 1) + bytes([253, 4, 0x86])
        data += bytes([0]) + struct.pack('<I', 1000000000)
        header = struct.pack('<BBHI4s', 14, 0x20, 100, len(data), b'.FIT')
        header += struct.pack('<H', compute_crc(header))
        raw = header + data
        raw += struct.pack('<H', compute_crc(raw))
        bad = raw[:-1] + bytes([raw[-1] ^ 0xff])
        rejected = self.client.post('/api/import/fit', files={'file': ('bad.fit', bad)}, headers=self.headers)
        self.assertEqual(rejected.status_code, 400)
        self.assertFalse((self.root/'data/raw/bad.fit').exists())
        accepted = self.client.post('/api/import/fit', files={'file': ('valid.fit', raw)}, headers=self.headers)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertTrue(accepted.json()['created'])
        repeated = self.client.post('/api/import/fit', files={'file': ('renamed.fit', raw)}, headers=self.headers)
        self.assertFalse(repeated.json()['created'])
        self.assertEqual(len(list((self.root/'data/raw').glob('*.fit'))), 1)


if __name__ == '__main__':
    unittest.main()
