import json
from pathlib import Path

from app.database import Database
from scripts.corpus_coverage import build_report


def test_package_coverage_requires_full_text_verified_documents(tmp_path: Path):
    database_path = tmp_path / "coverage.db"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({
        "registry_version": 1,
        "domain": "test",
        "packages": [{
            "id": "p1", "name": "Package", "priority": "P0", "status": "building",
            "mandatory_documents": ["complete", "partial"], "mandatory_source_families": [],
        }],
    }), encoding="utf-8")
    db = Database(database_path)
    with db.connect() as con:
        for document_id, completeness in (("complete", "full_text_verified"), ("partial", "partial")):
            con.execute(
                """INSERT INTO legal_documents
                (id,title,number,authority,official_url,content_hash,effective_from,legal_status,
                 jurisdiction,version,imported_at,completeness_status)
                VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
                (document_id, document_id, document_id, "Test", "https://example.gov.vn", "0" * 64,
                 "2024-01-01", "effective", "Vietnam", "v1", completeness),
            )

    report = build_report(database_path, registry_path)

    assert report["packages_ready"] == 0
    assert report["packages"][0]["acquired_documents"] == 2
    assert report["packages"][0]["verified_documents"] == 1
    assert report["packages"][0]["document_coverage_percent"] == 50.0


def test_package_coverage_accepts_source_families_with_verified_evidence(tmp_path: Path):
    database_path = tmp_path / "coverage.db"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({
        "registry_version": 1,
        "domain": "test",
        "packages": [{
            "id": "p1", "name": "Package", "priority": "P0", "status": "active",
            "mandatory_documents": ["law", "guidance"],
            "mandatory_source_families": [{
                "id": "guidance_family", "evidence_documents": ["guidance"],
            }],
        }],
    }), encoding="utf-8")
    db = Database(database_path)
    with db.connect() as con:
        for document_id in ("law", "guidance"):
            con.execute(
                """INSERT INTO legal_documents
                (id,title,number,authority,official_url,content_hash,effective_from,legal_status,
                 jurisdiction,version,imported_at,completeness_status)
                VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'),'full_text_verified')""",
                (document_id, document_id, document_id, "Test", "https://example.gov.vn", "0" * 64,
                 "2024-01-01", "effective", "Vietnam", "v1"),
            )

    report = build_report(database_path, registry_path)

    assert report["packages_ready"] == 1
    assert report["packages"][0]["pending_source_families"] == []
    assert report["packages"][0]["source_families"][0]["satisfied"] is True
