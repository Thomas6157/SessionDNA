"""Private SessionDNA API and locally built PWA. No external AI calls by default."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from import_calendar import parse_calendar
from import_training_week import import_week
from sessiondna_store import SQLiteStateStore
from training_week import validate_week


def read_json(path, fallback=None):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else fallback


class Catalog:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.RLock()
        self.signature = None
        self.data = {}

    def read(self):
        path = self.root / 'data/processed/triathlon/catalog.json'
        if not path.exists():
            return {'activities': [], 'profiles': {}, 'counts': {}, 'weeks': [], 'quality': {}}
        signature = (path.stat().st_mtime_ns, path.stat().st_size)
        with self.lock:
            if signature != self.signature:
                try:
                    self.data = read_json(path)
                except (ValueError, OSError) as exc:
                    raise HTTPException(503, 'Actualisation en cours; réessayer dans quelques secondes.') from exc
                self.signature = signature
            return self.data

    def activity(self, activity_id):
        for activity in self.read()['activities']:
            if activity['id'] == activity_id:
                return activity
        raise HTTPException(404, 'Séance inconnue.')

    def training(self):
        versions = {}
        for manifest_path in (self.root / 'data/training/weeks').glob('*/*/manifest.json'):
            manifest = read_json(manifest_path)
            source = manifest_path.with_name('source.json')
            raw = source.read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest['source_sha256']:
                raise HTTPException(409, 'Un programme source a changé après son import. Vérification nécessaire.')
            plan = json.loads(raw.decode('utf-8-sig'))
            audit = validate_week(plan)
            if audit['errors']:
                raise HTTPException(409, 'Programme archivé invalide; aucune correction automatique.')
            current = versions.get(plan['week_start'])
            if current is None or manifest['imported_utc'] > current['manifest']['imported_utc']:
                versions[plan['week_start']] = {'plan': plan, 'manifest': manifest}
        return [versions[k] for k in sorted(versions)]

    def bootstrap(self):
        data = {k: v for k, v in self.read().items() if k not in {'activities', 'profiles'}}
        data.update(
            app_version='2.0.0', timezone='Europe/Paris', training_weeks=self.training(),
            calendar=read_json(self.root / 'data/calendar/current.json'),
            planning_defaults=read_json(self.root / 'src/planning_preferences.json', {}),
            model_metrics=read_json(self.root / 'data/processed/sport_model/metrics.json'),
            features={'offline_feedback': True, 'immutable_plans': True, 'local_analytics': True, 'generative_ai': os.getenv('SESSIONDNA_AI_ENABLED') == '1'},
        )
        return data


class StateWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: str = Field(min_length=1, max_length=128)
    items: dict


class UpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sync: bool = False
    calendar_downloads: bool = False


class Jobs:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.Lock()
        self.process = None
        self.path = self.root / 'data/sync/app_job.json'

    def status(self):
        saved = read_json(self.path, {'status': 'idle'})
        # An unfinished job from another process is never represented as success.
        if saved.get('status') == 'running' and self.process is None:
            saved = {**saved, 'status': 'unknown', 'message': 'Exécution précédente à vérifier; aucun nouvel import lancé automatiquement.'}
        return saved

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        temp.replace(self.path)

    def start(self, options):
        with self.lock:
            if (self.process and self.process.poll() is None) or (self.root / 'data/sync/update.lock').exists():
                raise HTTPException(409, 'Une actualisation est déjà en cours.')
            command = [sys.executable, '-B', str(self.root / 'src/update_triathlon.py')]
            if options.sync:
                command.append('--sync')
            if options.calendar_downloads:
                command.append('--calendar-downloads')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            log = (self.path.parent / 'app_update.log').open('w', encoding='utf-8')
            self.process = subprocess.Popen(command, cwd=self.root, stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            started = datetime.now(timezone.utc).isoformat()
            self.save({'status': 'running', 'started_utc': started, 'sync': options.sync})
            process = self.process
            def finish():
                code = process.wait()
                log.close()
                with self.lock:
                    if self.process is process:
                        self.save({'status': 'completed' if code == 0 else 'failed', 'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(), 'exit_code': code, 'message': 'Actualisation terminée.' if code == 0 else 'Actualisation interrompue. Consulter le bilan local; si nécessaire renouveler la connexion Garmin dans le terminal.'})
            threading.Thread(target=finish, daemon=True).start()
            return self.status()


def create_app(root: Path | None = None, *, port=8765, public_origin=None, state_path=None):
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    app = FastAPI(title='SessionDNA', version='2.0.0', docs_url='/api/docs', openapi_url='/api/openapi.json', redoc_url=None)
    app.state.root = root
    app.state.catalog = Catalog(root)
    app.state.store = SQLiteStateStore(state_path or root / 'data/app_state/sessiondna.sqlite3', root / 'data/app_state/current.json')
    app.state.jobs = Jobs(root)
    hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
    origins = {f'http://127.0.0.1:{port}', f'http://localhost:{port}'}
    if public_origin:
        parsed = urlsplit(public_origin)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError('Origine privée HTTPS invalide.')
        hosts.add(parsed.netloc)
        origins.add('https://' + parsed.netloc)

    @app.middleware('http')
    async def boundaries(request: Request, call_next):
        host, origin = request.headers.get('host'), request.headers.get('origin')
        if host not in hosts or (origin and origin not in origins):
            return JSONResponse({'detail': 'Origine ou hôte non autorisé.'}, status_code=403)
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            if origin not in origins:
                return JSONResponse({'detail': 'Une requête depuis cette application est requise.'}, status_code=403)
            try:
                length = int(request.headers.get('content-length', '-1'))
            except ValueError:
                length = -1
            if not 0 <= length <= 40_000_000:
                return JSONResponse({'detail': 'Requête absente ou trop volumineuse.'}, status_code=413)
            content_type = request.headers.get('content-type', '').split(';')[0]
            if content_type not in {'application/json', 'multipart/form-data'}:
                return JSONResponse({'detail': 'Format de requête non accepté.'}, status_code=415)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(ValueError)
    async def invalid_value(_request, exc):
        return JSONResponse({'detail': str(exc)[:1000]}, status_code=400)

    @app.get('/api/health')
    def health():
        lock = root / 'data/sync/update.lock'
        return {'ok': True, 'version': '2.0.0', 'storage': 'sqlite', 'private_access': True, 'update_running': lock.exists(), 'ai_enabled': os.getenv('SESSIONDNA_AI_ENABLED') == '1'}

    @app.get('/api/bootstrap')
    def bootstrap():
        return app.state.catalog.bootstrap()

    @app.get('/api/activities')
    def activities(sport: str = '', search: str = '', offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500), start: str = '', end: str = ''):
        items = app.state.catalog.read()['activities']
        if sport and sport != 'all':
            items = [x for x in items if x.get('sport') == sport]
        if search:
            needle = search.casefold()
            items = [x for x in items if needle in ' '.join(str(x.get(k, '')) for k in ['id','filename','sport','start_utc','human_objective','human_format','title','name']).casefold()]
        if start or end:
            first = date.fromisoformat(start) if start else date.min
            last = date.fromisoformat(end) if end else date.max
            if first > last:
                raise ValueError('La date de début doit précéder la date de fin.')
            def local_day(item):
                try:
                    stamp = datetime.fromisoformat(item.get('start_utc', '').replace('Z', '+00:00'))
                    return stamp.astimezone(ZoneInfo('Europe/Paris')).date() if stamp.tzinfo else None
                except (ValueError, TypeError):
                    return None
            items = [x for x in items if (day := local_day(x)) is not None and first <= day <= last]
        items = sorted(items, key=lambda x: x.get('start_utc') or '', reverse=True)
        return {'items': items[offset:offset + limit], 'total': len(items), 'offset': offset, 'limit': limit}

    @app.get('/api/activities/{activity_id}')
    def activity(activity_id: str):
        entry = app.state.catalog.activity(activity_id)
        return {'activity': entry, 'profile': app.state.catalog.read().get('profiles', {}).get(activity_id, [])}

    analytics_lock = threading.RLock()
    def analytics_service():
        if not hasattr(app.state, 'analytics'):
            from sessiondna_analytics import AnalyticsService
            app.state.analytics = AnalyticsService(root)
        return app.state.analytics

    @app.get('/api/activities/{activity_id}/analysis')
    def activity_analysis(activity_id: str):
        app.state.catalog.activity(activity_id)
        with analytics_lock:
            return analytics_service().analyze(activity_id)

    @app.get('/api/activities/{activity_id}/route')
    def activity_route(activity_id: str):
        app.state.catalog.activity(activity_id)
        with analytics_lock:
            return analytics_service().route(activity_id)

    @app.get('/api/analytics/overview')
    def overview():
        with analytics_lock:
            return analytics_service().overview()

    @app.get('/api/state')
    def state_read():
        return app.state.store.read()

    @app.post('/api/state')
    def state_write(payload: StateWrite):
        result = app.state.store.write(payload.revision, payload.items)
        if result is None:
            return JSONResponse({'error': 'Une autre sauvegarde existe. Récupérer et résoudre les différences avant de renvoyer.', 'detail': 'Conflit de version.'}, status_code=409)
        return result

    @app.get('/api/state/history')
    def state_history():
        return {'items': app.state.store.history()}

    def weekly_report(week):
        from sessiondna_insights import build_weekly_insights
        return build_weekly_insights(root, week, app.state.store.read()['items'])

    @app.get('/api/insights')
    def insights(week: str | None = None, week_start: str | None = None):
        return weekly_report(week or week_start)

    @app.get('/api/insights/export')
    def insights_export(week: str | None = None, week_start: str | None = None):
        from sessiondna_insights import render_markdown
        report = weekly_report(week or week_start)
        return Response(render_markdown(report), media_type='text/markdown; charset=utf-8', headers={'Content-Disposition': 'attachment; filename="bilan-sessiondna.md"'})

    @app.post('/api/insights/generate')
    async def insights_generate(payload: dict):
        from sessiondna_insights import generate_ai_brief
        config = {'enabled': os.getenv('SESSIONDNA_AI_ENABLED') == '1', 'provider': os.getenv('SESSIONDNA_AI_PROVIDER', 'ollama'), 'model': os.getenv('SESSIONDNA_AI_MODEL', ''), 'base_url': os.getenv('SESSIONDNA_AI_BASE_URL', 'http://127.0.0.1:11434/v1'), 'api_key': os.getenv('SESSIONDNA_AI_API_KEY', '')}
        # Provider configuration is administrator-controlled, never a user supplied URL.
        try:
            return await generate_ai_brief(weekly_report(payload.get('week') or payload.get('week_start')), config)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get('/api/jobs/latest')
    def latest_job():
        return app.state.jobs.status()

    @app.post('/api/update', status_code=202)
    def update(payload: UpdateRequest):
        return app.state.jobs.start(payload)

    import_lock = threading.Lock()
    async def upload(file, extension):
        name = file.filename or ''
        if Path(name).suffix.lower() != extension:
            raise HTTPException(400, 'Extension attendue: ' + extension)
        content = await file.read(35_000_001)
        await file.close()
        if not content or len(content) > 35_000_000:
            raise HTTPException(400, 'Fichier vide ou trop volumineux.')
        return content

    @app.post('/api/import/training')
    async def import_training(file: UploadFile = File(...)):
        raw = await upload(file, '.json')
        parsed = json.loads(raw.decode('utf-8-sig'))
        try:
            audit = validate_week(parsed)
        except (KeyError, TypeError, UnicodeError) as exc:
            raise ValueError('Structure du programme invalide. Aucun programme importé.') from exc
        if audit['errors']:
            raise ValueError('; '.join(audit['errors']))
        with import_lock, tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'training.json'
            source.write_bytes(raw)
            folder, created = import_week(source, root / 'data/training/weeks')
        return {'ok': True, 'summary': 'Nouvelle version conservée.' if created else 'Cette version est déjà présente.', 'created': created, 'manifest': read_json(folder / 'manifest.json')}

    @app.post('/api/import/calendar')
    async def import_calendar(file: UploadFile = File(...)):
        raw = await upload(file, '.ics')
        try:
            result = parse_calendar(raw)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('Export iCalendar invalide ou non pris en charge. Ancien calendrier conservé.') from exc
        digest = hashlib.sha256(raw).hexdigest()
        result.update(source_sha256=digest, imported_utc=datetime.now(timezone.utc).isoformat(), automatic_sync=False)
        with import_lock:
            folder = root / 'data/calendar'
            sources = folder / 'sources'
            sources.mkdir(parents=True, exist_ok=True)
            (sources / (digest + '.ics')).write_bytes(raw)
            target = folder / 'current.json'
            temp = folder / 'current.api.tmp'
            temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            temp.replace(target)
        return {'ok': True, 'summary': f"{len(result['events'])} cours importés depuis cet export.", 'automatic_sync': False, 'events': len(result['events'])}

    @app.post('/api/import/fit')
    async def import_fit(file: UploadFile = File(...)):
        raw = await upload(file, '.fit')
        import fitdecode
        try:
            with fitdecode.FitReader(io.BytesIO(raw)) as reader:
                # Finish decoding the file: a valid early session must not hide a corrupt tail.
                found = False
                for frame in reader:
                    found |= isinstance(frame, fitdecode.FitDataMessage) and frame.name == 'session'
                if not found:
                    raise ValueError('Aucun résumé de session FIT reconnu.')
        except Exception as exc:
            raise ValueError('Fichier FIT invalide ou incomplet. Aucun fichier ajouté.') from exc
        digest = hashlib.sha256(raw).hexdigest()
        with import_lock:
            raw_dir = root / 'data/raw'
            raw_dir.mkdir(parents=True, exist_ok=True)
            for existing in raw_dir.glob('*'):
                if existing.is_file() and existing.suffix.lower() == '.fit' and existing.stat().st_size == len(raw) and hashlib.sha256(existing.read_bytes()).hexdigest() == digest:
                    return {'ok': True, 'created': False, 'summary': 'Fichier déjà présent; aucun doublon ajouté.'}
            clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', Path(file.filename or 'activity.fit').name)
            target = raw_dir / clean_name
            if target.exists():
                target = raw_dir / (digest[:16] + '_ACTIVITY.fit')
            with target.open('xb') as stream:
                stream.write(raw)
        return {'ok': True, 'created': True, 'summary': 'FIT conservé. Actualiser les analyses pour le voir dans le catalogue.', 'needs_update': True}

    @app.get('/api/backup')
    def backup():
        content = io.BytesIO()
        with zipfile.ZipFile(content, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('state.json', json.dumps({'schema_version': 'sessiondna.backup.v2', 'exported_utc': datetime.now(timezone.utc).isoformat(), **app.state.store.read()}, ensure_ascii=False))
            for folder in ['data/training/weeks', 'data/calendar', 'data/processed/supervised']:
                for path in (root / folder).rglob('*'):
                    if path.is_file() and path.suffix in {'.json','.ics','.csv'}:
                        archive.write(path, path.relative_to(root).as_posix())
            archive.writestr('README.txt', 'Sauvegarde portable SessionDNA. state.json conserve retours, annotations et horaires. Programmes sources intacts. Les FIT bruts et jetons Garmin ne sont pas inclus. Restaurer les saisies via import JSON dans les réglages.')
        return Response(content.getvalue(), media_type='application/zip', headers={'Content-Disposition': 'attachment; filename="sessiondna-backup.zip"'})

    @app.get('/api/learning')
    def learning():
        return read_json(root / 'docs/integrations.json', {'integrations': []})

    legacy = root / 'data/processed/triathlon_app'
    if legacy.is_dir():
        app.mount('/legacy', StaticFiles(directory=legacy, html=True), name='legacy')
    web = root / 'app/dist'
    if web.is_dir():
        if (web / 'assets').is_dir():
            app.mount('/assets', StaticFiles(directory=web / 'assets'), name='assets')
        @app.get('/{path:path}')
        def frontend(path: str):
            if path.startswith('api/'):
                raise HTTPException(404, 'Endpoint inconnu.')
            target = (web / path).resolve()
            if not target.is_relative_to(web.resolve()):
                raise HTTPException(403)
            if target.is_file():
                return FileResponse(target, headers={'Cache-Control': 'no-cache' if target.name in {'sw.js','index.html'} else 'private, max-age=3600'})
            if Path(path).suffix:
                raise HTTPException(404)
            return FileResponse(web / 'index.html', headers={'Cache-Control': 'no-cache'})
    return app


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--public-origin', default=read_json(root / 'data/app_state/access.json', {}).get('public_origin'))
    parser.add_argument('--state-file', type=Path, default=root / 'data/app_state/sessiondna.sqlite3')
    args = parser.parse_args()
    if not (root / 'app/dist/index.html').exists():
        parser.error('Construire app/ avant le lancement (voir README).')
    import uvicorn
    print(f'SessionDNA : http://127.0.0.1:{args.port} — garder ce terminal ouvert.', flush=True)
    uvicorn.run(create_app(root, port=args.port, public_origin=args.public_origin, state_path=args.state_file), host='127.0.0.1', port=args.port, proxy_headers=False, log_level='warning')


if __name__ == '__main__':
    main()
