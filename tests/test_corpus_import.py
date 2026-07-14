import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from app.database import Database
from scripts.import_source_pack import import_pack, validate


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _complete_pack(tmp_path: Path) -> tuple[Path, dict]:
    artifact = tmp_path / "official.pdf"
    artifact.write_bytes(b"official complete artifact")
    full_text = tmp_path / "full.txt"
    full_text.write_text("Điều 1. Phạm vi\nNội dung 1\nĐiều 2. Hiệu lực\nNội dung 2", encoding="utf-8")
    pack = {
        "schema_version": 2,
        "document": {
            "id": "law-complete",
            "title": "Luật kiểm thử toàn văn",
            "number": "01/TEST",
            "authority": "Quốc hội",
            "official_url": "https://example.gov.vn/law",
            "content_hash": _hash(artifact),
            "issued_date": "2024-01-01",
            "effective_from": "2024-07-01",
            "effective_to": None,
            "legal_status": "effective",
            "jurisdiction": "Vietnam",
            "locality": None,
            "version": "original",
            "document_type": "law",
            "source_format": "pdf",
            "completeness_status": "full_text_verified",
            "full_text_file": "full.txt",
            "full_text_hash": _hash(full_text),
            "expected_article_count": 2,
            "extraction_method": "test",
            "verified_at": "2026-07-14T00:00:00Z",
            "verified_by": "test-reviewer",
            "source_artifacts": [{
                "path": "official.pdf",
                "official_url": "https://example.gov.vn/law.pdf",
                "sha256": _hash(artifact),
                "media_type": "application/pdf",
                "page_count": 1,
            }],
        },
        "provisions": [
            {"id": "law-complete-art-1", "location": "Điều 1", "level": "article", "ordinal": 1, "number": "1", "text": "Điều 1. Phạm vi\nNội dung 1"},
            {"id": "law-complete-art-2", "location": "Điều 2", "level": "article", "ordinal": 2, "number": "2", "text": "Điều 2. Hiệu lực\nNội dung 2"},
        ],
    }
    pack_path = tmp_path / "pack.json"
    pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    return pack_path, pack


def test_full_text_pack_is_verified_and_imported(tmp_path: Path):
    pack_path, _ = _complete_pack(tmp_path)
    database_path = tmp_path / "corpus.db"

    document_id, count = import_pack(pack_path, database_path)

    assert document_id == "law-complete"
    assert count == 2
    con = sqlite3.connect(database_path)
    row = con.execute(
        "SELECT completeness_status,expected_article_count,parsed_article_count,length(full_text) FROM legal_documents"
    ).fetchone()
    assert row[:3] == ("full_text_verified", 2, 2)
    assert row[3] > 50
    assert con.execute("SELECT count(*) FROM legal_source_artifacts").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM legal_provisions WHERE level='article'").fetchone()[0] == 2
    con.close()


def test_source_pack_can_be_reimported_without_breaking_foreign_keys(tmp_path: Path):
    pack_path, _ = _complete_pack(tmp_path)
    database_path = tmp_path / "corpus.db"

    import_pack(pack_path, database_path)
    document_id, count = import_pack(pack_path, database_path)

    assert document_id == "law-complete"
    assert count == 2
    con = sqlite3.connect(database_path)
    assert con.execute("SELECT count(*) FROM legal_documents").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM legal_provisions").fetchone()[0] == 2
    con.close()


def test_verified_pack_rejects_artifact_hash_mismatch(tmp_path: Path):
    pack_path, pack = _complete_pack(tmp_path)
    pack["document"]["source_artifacts"][0]["sha256"] = "0" * 64
    pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        validate(pack, pack_path)


def test_partial_legacy_pack_cannot_be_mistaken_for_complete(tmp_path: Path):
    digest = hashlib.sha256(b"excerpt").hexdigest()
    pack = {
        "document": {
            "id": "legacy-excerpt", "title": "Trích đoạn", "number": "X/TEST",
            "authority": "Test", "official_url": "https://example.gov.vn/x",
            "content_hash": digest, "effective_from": "2024-01-01",
            "legal_status": "effective", "jurisdiction": "Vietnam", "version": "demo",
        },
        "provisions": [{"id": "legacy-1", "location": "Điều 1", "text": "Một đoạn trích"}],
    }
    pack_path = tmp_path / "legacy.json"
    pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    database_path = tmp_path / "legacy.db"

    import_pack(pack_path, database_path)

    con = sqlite3.connect(database_path)
    row = con.execute("SELECT completeness_status,full_text FROM legal_documents").fetchone()
    assert row == ("partial", None)
    con.close()


def test_database_migrates_existing_corpus_tables(tmp_path: Path):
    database_path = tmp_path / "old.db"
    con = sqlite3.connect(database_path)
    con.executescript("""
        CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
        CREATE TABLE legal_documents (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, number TEXT NOT NULL,
          authority TEXT NOT NULL, official_url TEXT NOT NULL, content_hash TEXT NOT NULL,
          issued_date TEXT, effective_from TEXT NOT NULL, effective_to TEXT,
          legal_status TEXT NOT NULL, jurisdiction TEXT NOT NULL, locality TEXT,
          version TEXT NOT NULL, imported_at TEXT NOT NULL
        );
        CREATE TABLE legal_provisions (
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
          location TEXT NOT NULL, text TEXT NOT NULL, keywords TEXT NOT NULL
        );
    """)
    con.close()

    Database(database_path)

    con = sqlite3.connect(database_path)
    document_columns = {row[1] for row in con.execute("PRAGMA table_info(legal_documents)")}
    provision_columns = {row[1] for row in con.execute("PRAGMA table_info(legal_provisions)")}
    assert {"full_text", "full_text_hash", "completeness_status"} <= document_columns
    assert {"level", "ordinal", "source_page_start", "text_hash"} <= provision_columns
    assert con.execute("SELECT 1 FROM schema_migrations WHERE version=2").fetchone()
    con.close()
