from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, purpose TEXT NOT NULL,
  status TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
  property_ids TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS facts (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), key TEXT NOT NULL,
  value TEXT NOT NULL, provenance TEXT NOT NULL, actor_id TEXT NOT NULL,
  source_id TEXT, method TEXT NOT NULL, created_at TEXT NOT NULL, supersedes_id TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), type TEXT NOT NULL,
  version INTEGER NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL,
  dependency_version INTEGER NOT NULL, stale INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, event_type TEXT NOT NULL,
  actor_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_keys (
  id TEXT PRIMARY KEY, key_hash TEXT NOT NULL UNIQUE, actor_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS legal_documents (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, number TEXT NOT NULL,
  authority TEXT NOT NULL, official_url TEXT NOT NULL, content_hash TEXT NOT NULL,
  issued_date TEXT, effective_from TEXT NOT NULL, effective_to TEXT,
  legal_status TEXT NOT NULL, jurisdiction TEXT NOT NULL, locality TEXT,
  version TEXT NOT NULL, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS legal_provisions (
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES legal_documents(id),
  location TEXT NOT NULL, text TEXT NOT NULL, keywords TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
  role TEXT NOT NULL, content TEXT NOT NULL, citations TEXT NOT NULL DEFAULT '[]',
  actor_id TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_case ON facts(case_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_case ON artifacts(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_events(case_id);
CREATE INDEX IF NOT EXISTS idx_api_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_provisions_document ON legal_provisions(document_id);
CREATE INDEX IF NOT EXISTS idx_messages_case ON messages(case_id,created_at);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(SCHEMA)
            con.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(1,datetime('now'))")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    @staticmethod
    def decode(row):
        return dict(row) if row else None

    @staticmethod
    def json(value) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)
