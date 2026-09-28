"""Storage and service boundaries shared by local stages and future cloud adapters."""
from contextlib import closing
import hashlib
import json
from itertools import islice
import os
from pathlib import Path
import sqlite3
from typing import Protocol, Iterable


def chunks(rows, size):
    if size < 1:
        raise ValueError('Chunk size must be positive')
    iterator = iter(rows)
    while batch := list(islice(iterator, size)):
        yield batch


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


class StageStore(Protocol):
    def rows(self, stage: str, start: str = '', end: str | None = None) -> Iterable[dict]: ...
    def put(self, stage: str, key: str, payload: dict) -> None: ...
    def get(self, stage: str, key: str) -> dict | None: ...


class DecisionService(Protocol):
    checkpoint_id: str
    def submit_batch(self, candidates: list) -> list: ...


class SQLiteStageStore:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with closing(self.connect()) as conn, conn:
            conn.execute('CREATE TABLE IF NOT EXISTS chunk_records(stage TEXT,key TEXT,payload TEXT,PRIMARY KEY(stage,key))')

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.execute('PRAGMA cache_size=-2048')
        conn.execute('PRAGMA temp_store=FILE')
        return conn

    def put(self, stage, key, payload):
        with closing(self.connect()) as conn, conn:
            conn.execute('INSERT OR REPLACE INTO chunk_records VALUES (?,?,?)', (stage, key, json.dumps(payload, sort_keys=True)))

    def get(self, stage, key):
        with closing(self.connect()) as conn:
            row = conn.execute('SELECT payload FROM chunk_records WHERE stage=? AND key=?', (stage,key)).fetchone()
            return json.loads(row[0]) if row else None

    def rows(self, stage, start='', end=None):
        with closing(self.connect()) as conn:
            for (payload,) in conn.execute('SELECT payload FROM chunk_records WHERE stage=? AND key>=? AND (? IS NULL OR key<?) ORDER BY key', (stage,start,end,end)):
                yield json.loads(payload)

    def run_chunk(self, stage, key, inputs, transform, contract):
        fingerprint = digest([inputs, contract])
        previous = self.get('checkpoints', stage+':'+key)
        if previous and previous['fingerprint'] == fingerprint:
            return self.get(stage,key)
        output = transform(inputs)
        # Results and checkpoint commit atomically; a failed chunk is safe to replay.
        with closing(self.connect()) as conn, conn:
            conn.executemany('INSERT OR REPLACE INTO chunk_records VALUES (?,?,?)',
                [(stage,key,json.dumps(output)), ('checkpoints',stage+':'+key,json.dumps(dict(fingerprint=fingerprint)))])
        return output


def open_store(config):
    backend = config.get('backend', 'sqlite')
    if backend != 'sqlite':
        raise NotImplementedError(f'{backend} adapter is a future deployment boundary; no silent SQLite fallback')
    return SQLiteStageStore(config['db_path'])
