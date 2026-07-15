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
  version TEXT NOT NULL, imported_at TEXT NOT NULL,
  document_type TEXT NOT NULL DEFAULT 'unknown', source_format TEXT,
  full_text TEXT, full_text_hash TEXT,
  completeness_status TEXT NOT NULL DEFAULT 'partial',
  expected_article_count INTEGER, parsed_article_count INTEGER,
  extraction_method TEXT, verified_at TEXT, verified_by TEXT
  ,artifact_integrity_status TEXT NOT NULL DEFAULT 'unverified'
  ,extraction_quality_status TEXT NOT NULL DEFAULT 'unreviewed'
  ,legal_review_status TEXT NOT NULL DEFAULT 'unreviewed'
  ,lifecycle_status TEXT NOT NULL DEFAULT 'unreviewed'
  ,runtime_activation_status TEXT NOT NULL DEFAULT 'inactive'
  ,review_fingerprint TEXT
);
CREATE TABLE IF NOT EXISTS legal_provisions (
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES legal_documents(id),
  location TEXT NOT NULL, text TEXT NOT NULL, keywords TEXT NOT NULL,
  parent_id TEXT, level TEXT NOT NULL DEFAULT 'provision', ordinal INTEGER,
  number TEXT, heading TEXT, source_page_start INTEGER, source_page_end INTEGER,
  source_artifact_id TEXT,
  effective_from TEXT, effective_to TEXT,
  legal_status TEXT NOT NULL DEFAULT 'effective', text_hash TEXT
);
CREATE TABLE IF NOT EXISTS legal_source_artifacts (
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES legal_documents(id),
  part_number INTEGER NOT NULL, official_url TEXT NOT NULL, local_path TEXT NOT NULL,
  media_type TEXT NOT NULL, sha256 TEXT NOT NULL, page_count INTEGER,
  byte_size INTEGER NOT NULL, fetched_at TEXT NOT NULL, verified_at TEXT,
  UNIQUE(document_id,part_number)
);
CREATE TABLE IF NOT EXISTS legal_document_relationships (
  id TEXT PRIMARY KEY,
  source_document_id TEXT NOT NULL REFERENCES legal_documents(id),
  source_provision_id TEXT, target_document_id TEXT NOT NULL,
  target_provision_id TEXT, relation_type TEXT NOT NULL,
  effective_from TEXT, evidence_location TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS corpus_runtime_state (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  revision INTEGER NOT NULL DEFAULT 0,
  activated_at TEXT,
  activation_status TEXT NOT NULL DEFAULT 'not_activated',
  report_json TEXT NOT NULL DEFAULT '{}'
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
CREATE INDEX IF NOT EXISTS idx_artifacts_document ON legal_source_artifacts(document_id);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON legal_document_relationships(source_document_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON legal_document_relationships(target_document_id);
CREATE INDEX IF NOT EXISTS idx_messages_case ON messages(case_id,created_at);
INSERT OR IGNORE INTO corpus_runtime_state(singleton,revision,activation_status,report_json)
VALUES(1,0,'not_activated','{}');
"""


DOCUMENT_COLUMNS_V2 = {
    "document_type": "TEXT NOT NULL DEFAULT 'unknown'",
    "source_format": "TEXT",
    "full_text": "TEXT",
    "full_text_hash": "TEXT",
    "completeness_status": "TEXT NOT NULL DEFAULT 'partial'",
    "expected_article_count": "INTEGER",
    "parsed_article_count": "INTEGER",
    "extraction_method": "TEXT",
    "verified_at": "TEXT",
    "verified_by": "TEXT",
}

DOCUMENT_GOVERNANCE_COLUMNS_V4 = {
    "artifact_integrity_status": "TEXT NOT NULL DEFAULT 'unverified'",
    "extraction_quality_status": "TEXT NOT NULL DEFAULT 'unreviewed'",
    "legal_review_status": "TEXT NOT NULL DEFAULT 'unreviewed'",
    "lifecycle_status": "TEXT NOT NULL DEFAULT 'unreviewed'",
    "runtime_activation_status": "TEXT NOT NULL DEFAULT 'inactive'",
    "review_fingerprint": "TEXT",
}

PROVISION_COLUMNS_V2 = {
    "parent_id": "TEXT",
    "level": "TEXT NOT NULL DEFAULT 'provision'",
    "ordinal": "INTEGER",
    "number": "TEXT",
    "heading": "TEXT",
    "source_page_start": "INTEGER",
    "source_page_end": "INTEGER",
    "source_artifact_id": "TEXT",
    "effective_from": "TEXT",
    "effective_to": "TEXT",
    "legal_status": "TEXT NOT NULL DEFAULT 'effective'",
    "text_hash": "TEXT",
}


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(SCHEMA)
            con.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(1,datetime('now'))")
            self._migrate_v2(con)
            self._migrate_v3(con)
            self._migrate_v4(con)

    @staticmethod
    def _migrate_v2(con: sqlite3.Connection) -> None:
        for table, columns in (
            ("legal_documents", DOCUMENT_COLUMNS_V2),
            ("legal_provisions", PROVISION_COLUMNS_V2),
        ):
            existing = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        con.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(2,datetime('now'))")

    @staticmethod
    def _migrate_v3(con: sqlite3.Connection) -> None:
        con.execute(
            """CREATE TABLE IF NOT EXISTS corpus_runtime_state (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            revision INTEGER NOT NULL DEFAULT 0,
            activated_at TEXT,
            activation_status TEXT NOT NULL DEFAULT 'not_activated',
            report_json TEXT NOT NULL DEFAULT '{}')"""
        )
        con.execute(
            """INSERT OR IGNORE INTO corpus_runtime_state
            (singleton,revision,activation_status,report_json)
            VALUES(1,0,'not_activated','{}')"""
        )
        con.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(3,datetime('now'))")

    @staticmethod
    def _migrate_v4(con: sqlite3.Connection) -> None:
        existing = {row[1] for row in con.execute("PRAGMA table_info(legal_documents)")}
        for name, definition in DOCUMENT_GOVERNANCE_COLUMNS_V4.items():
            if name not in existing:
                con.execute(f"ALTER TABLE legal_documents ADD COLUMN {name} {definition}")
        con.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(4,datetime('now'))")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        finally:
            con.close()

    @staticmethod
    def decode(row):
        return dict(row) if row else None

    def corpus_revision(self) -> int:
        with self.connect() as con:
            row = con.execute(
                "SELECT revision FROM corpus_runtime_state WHERE singleton=1"
            ).fetchone()
        return int(row["revision"]) if row else 0

    @staticmethod
    def json(value) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)
