"""Versioned, transactional personal state. Original JSON backups stay intact."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

EXTRA_KEYS = {'sessiondna-annotations-v2', 'sessiondna-journal-v1'}


def validate_items(items):
    if not isinstance(items, dict) or len(items) > 500:
        raise ValueError('La sauvegarde doit être un objet de moins de 500 espaces.')
    for key, value in items.items():
        if not isinstance(key, str) or len(key) > 150:
            raise ValueError('Identifiant de sauvegarde invalide.')
        if not (key == 'sessiondna-planning-v1' or key.startswith('sessiondna-feedback-v1-') or key in EXTRA_KEYS):
            raise ValueError('Espace de sauvegarde non autorisé.')
        if not isinstance(value, dict):
            raise ValueError('Chaque espace doit contenir un objet.')
    try:
        encoded = json.dumps(items, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError('Données non sérialisables ou nombre invalide.') from exc
    if len(encoded.encode('utf-8')) > 2_000_000:
        raise ValueError('Sauvegarde supérieure à 2 Mo.')
    return encoded


class SQLiteStateStore:
    """A compare-and-swap write is one SQLite transaction, including its history."""

    def __init__(self, path: Path, legacy: Path | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1), revision TEXT NOT NULL, items TEXT NOT NULL, updated_utc TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, revision TEXT NOT NULL, items TEXT NOT NULL, created_utc TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM state WHERE id=1').fetchone() is None:
                initial = {'revision': 'empty', 'items': {}}
                if legacy and Path(legacy).exists():
                    initial = json.loads(Path(legacy).read_text(encoding='utf-8'))
                    validate_items(initial['items'])
                    if not isinstance(initial.get('revision'), str):
                        raise ValueError('Ancien état illisible: aucune migration effectuée.')
                    db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('legacy_source', str(legacy)))
                raw = validate_items(initial['items'])
                now = datetime.now(timezone.utc).isoformat()
                db.execute('INSERT INTO state VALUES (1,?,?,?)', (initial['revision'], raw, now))
                db.execute('INSERT INTO history(revision,items,created_utc) VALUES (?,?,?)', (initial['revision'], raw, now))

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.execute('PRAGMA busy_timeout=15000')
        connection.execute('PRAGMA foreign_keys=ON')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def read(self):
        with self.connect() as db:
            row = db.execute('SELECT revision,items FROM state WHERE id=1').fetchone()
        return {'revision': row[0], 'items': json.loads(row[1])}

    def write(self, revision, items):
        raw = validate_items(items)
        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT revision FROM state WHERE id=1').fetchone()[0]
            if current != revision:
                return None
            if current != digest:
                now = datetime.now(timezone.utc).isoformat()
                db.execute('UPDATE state SET revision=?,items=?,updated_utc=? WHERE id=1', (digest, raw, now))
                db.execute('INSERT INTO history(revision,items,created_utc) VALUES (?,?,?)', (digest, raw, now))
        return {'revision': digest, 'items': items}

    def history(self):
        with self.connect() as db:
            rows = db.execute('SELECT id,revision,created_utc FROM history ORDER BY id DESC LIMIT 100').fetchall()
        return [dict(id=r[0], revision=r[1], created_utc=r[2]) for r in rows]

    def snapshot(self, target):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as source, closing(sqlite3.connect(target)) as backup:
            source.backup(backup)
        return target
