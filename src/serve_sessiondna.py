"""Serveur local : n'expose que le dossier généré de l'application."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import argparse
import functools
import json
import hashlib
import threading
from urllib.parse import urlsplit

class StateStore:
    """Écriture atomique et contrôle de version ; archives hors du dossier web."""
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()

    def read(self):
        if not self.path.exists(): return {'revision': 'empty', 'items': {}}
        return json.loads(self.path.read_text(encoding='utf-8'))

    def write(self, revision, items):
        if not isinstance(items, dict) or len(items)>500: raise ValueError('Invalid items')
        for key, value in items.items():
            if not (key == 'sessiondna-planning-v1' or key.startswith('sessiondna-feedback-v1-')):
                raise ValueError('Unknown key')
            if len(key)>150 or not isinstance(value, dict): raise ValueError('Invalid value')
        raw = json.dumps(items, ensure_ascii=False, sort_keys=True, allow_nan=False)
        if len(raw.encode('utf-8'))>2_000_000: raise ValueError('Too large')
        with self.lock:
            current = self.read()
            if current['revision'] != revision: return None
            digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
            result = {'revision': digest, 'items': items}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            archive = self.path.parent/'history'; archive.mkdir(exist_ok=True)
            content = json.dumps(result, ensure_ascii=False, allow_nan=False)
            (archive/(digest+'.json')).write_text(content, encoding='utf-8')
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(content, encoding='utf-8'); temporary.replace(self.path)
            return result

class Handler(SimpleHTTPRequestHandler):
    def permitted(self, write=False):
        if self.headers.get('Host') not in self.server.allowed_hosts:
            self.send_error(403, 'Host not allowed'); return False
        origin = self.headers.get('Origin')
        if origin and origin not in self.server.allowed_origins:
            self.send_error(403, 'Origin not allowed'); return False
        if write and (not origin or self.headers.get('Content-Type') != 'application/json'):
            self.send_error(403, 'Same-origin JSON required'); return False
        return True

    def reply(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        if not self.permitted(): return
        if self.path == '/api/state':
            try: self.reply(200, self.server.store.read())
            except (ValueError, OSError): self.reply(500, {'error':'Sauvegarde serveur illisible ; conservée sans modification.'})
        else: super().do_GET()

    def do_POST(self):
        if not self.permitted(write=True): return
        if self.path != '/api/state': self.send_error(404); return
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 2_000_000: raise ValueError('Invalid size')
            body = json.loads(self.rfile.read(length))
            result = self.server.store.write(body['revision'], body['items'])
            self.reply(409 if result is None else 200, result or {'error':'Une autre sauvegarde a changé. Réessayer la synchronisation.'})
        except (ValueError, KeyError, TypeError): self.reply(400, {'error':'Sauvegarde invalide ; aucune modification.'})
        except OSError: self.reply(500, {'error':'Écriture impossible ; réessayer après vérification du disque.'})
    def list_directory(self,path):
        self.send_error(403,'Directory listing disabled')
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
    def send_head(self):
        if not self.permitted(): return None
        target=Path(self.translate_path(self.path)).resolve()
        if not target.is_relative_to(Path(self.directory).resolve()):
            self.send_error(403); return None
        return super().send_head()

def main():
    config_file=Path(__file__).resolve().parent.parent/'data/app_state/access.json'
    config=json.loads(config_file.read_text(encoding='utf-8')) if config_file.exists() else {}
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent.parent/'data/processed/triathlon_app')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--state-file',type=Path,default=Path(__file__).resolve().parent.parent/'data/app_state/current.json')
    p.add_argument('--public-origin',default=config.get('public_origin'),help='Origine HTTPS privée autorisée, par exemple celle de Tailscale Serve')
    a=p.parse_args()
    if not (a.directory/'index.html').is_file(): p.error('Construire l’application avant de démarrer le serveur.')
    server=ThreadingHTTPServer(('127.0.0.1',a.port),functools.partial(Handler,directory=str(a.directory.resolve())))
    server.store=StateStore(a.state_file)
    server.allowed_hosts={f'127.0.0.1:{a.port}',f'localhost:{a.port}'}
    server.allowed_origins={f'http://127.0.0.1:{a.port}',f'http://localhost:{a.port}'}
    if a.public_origin:
        origin=urlsplit(a.public_origin)
        if origin.scheme!='https' or not origin.hostname or origin.path not in ('','/') or origin.query or origin.fragment or origin.username or origin.password:
            p.error('--public-origin doit être une origine HTTPS sans chemin ni identifiants.')
        server.allowed_hosts.add(origin.netloc)
        server.allowed_origins.add('https://'+origin.netloc)
    print(f'SessionDNA : http://127.0.0.1:{a.port} — Ctrl+C pour arrêter.',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__':
    import sys
    if '--legacy' in sys.argv:
        sys.argv.remove('--legacy')
        main()
    elif (Path(__file__).resolve().parents[1]/'app/dist/index.html').exists():
        from sessiondna_api import main as serve_v2
        serve_v2()
    else:
        main()

