import sys
import tempfile
import unittest
import hashlib
import json
import os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from refresh_calendar import candidate

class RefreshTests(unittest.TestCase):
    def test_new_identical_and_old_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);current=folder/'current.json';export=folder/'mon_calendrier.ics'
            self.assertIsNone(candidate(folder,current))
            export.write_bytes(b'one')
            self.assertEqual(candidate(folder,current),export)
            current.write_text(json.dumps({'source_sha256':hashlib.sha256(b'one').hexdigest(),'imported_utc':'2026-01-01T00:00:00+00:00'}))
            self.assertIsNone(candidate(folder,current))
            export.write_bytes(b'two');os.utime(export,(1900000000,1900000000))
            self.assertEqual(candidate(folder,current),export)
            os.utime(export,(1000000000,1000000000));self.assertIsNone(candidate(folder,current))

if __name__=='__main__':unittest.main()
