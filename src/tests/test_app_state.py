import sys
import tempfile
import unittest
import threading
import functools
import json
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from serve_sessiondna import StateStore, Handler

class StateTests(unittest.TestCase):
    def test_version_and_archives(self):
        with tempfile.TemporaryDirectory() as folder:
            s=StateStore(Path(folder)/'current.json')
            self.assertEqual(s.read()['revision'],'empty')
            first=s.write('empty',{'sessiondna-planning-v1':{'weeks':{}}})
            self.assertIsNotNone(first)
            self.assertIsNone(s.write('empty',{}))
            self.assertEqual(s.read(),first)
            second=s.write(first['revision'],{})
            self.assertIsNotNone(second)
            self.assertEqual(len(list((Path(folder)/'history').glob('*.json'))),2)
    def test_reject_other_data(self):
        with tempfile.TemporaryDirectory() as folder:
            s=StateStore(Path(folder)/'current.json')
            with self.assertRaises(ValueError):s.write('empty',{'garmin_password':{}})
            self.assertFalse(s.path.exists())

    def test_http_origin_revision_and_private_files(self):
        with tempfile.TemporaryDirectory() as folder:
            web=Path(folder)/'web';web.mkdir();(web/'index.html').write_text('ok')
            server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(web)))
            address=f'127.0.0.1:{server.server_port}';origin='http://'+address
            server.allowed_hosts={address};server.allowed_origins={origin}
            server.store=StateStore(Path(folder)/'private/current.json')
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                def request(path,headers={},body=None):
                    req=urllib.request.Request(origin+path,headers=headers,data=None if body is None else json.dumps(body).encode())
                    try:
                        with urllib.request.urlopen(req,timeout=3) as r:return r.status,r.read()
                    except urllib.error.HTTPError as e:return e.code,e.read()
                self.assertEqual(request('/api/state')[0],200)
                self.assertEqual(request('/api/state',{'Host':'attacker.example'})[0],403)
                payload={'revision':'empty','items':{'sessiondna-planning-v1':{}}}
                self.assertEqual(request('/api/state',{'Content-Type':'application/json','Origin':'https://attacker.example'},payload)[0],403)
                headers={'Content-Type':'application/json','Origin':origin}
                self.assertEqual(request('/api/state',headers,payload)[0],200)
                self.assertEqual(request('/api/state',headers,payload)[0],409)
                self.assertEqual(request('/private/current.json')[0],404)
            finally:
                server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
