import hashlib
import json
from pathlib import Path

from scripts.verify_source_pack import build_report


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_structurally_valid_unverified_pack_is_not_activation_eligible(tmp_path):
    artifact = tmp_path / "official.pdf"
    artifact.write_bytes(b"official")
    full_text = tmp_path / "full.txt"
    full_text.write_text("Điều 1. Một\nNội dung\nĐiều 2. Hai\nNội dung", encoding="utf-8")
    pack = {
        "document": {
            "id": "law-test", "title": "Luật thử", "number": "01/TEST",
            "authority": "Quốc hội", "official_url": "https://example.gov.vn/law",
            "content_hash": _hash(artifact), "effective_from": "2024-01-01",
            "legal_status": "effective", "jurisdiction": "Vietnam", "version": "original",
            "completeness_status": "full_text_unverified", "full_text_file": "full.txt",
            "full_text_hash": _hash(full_text), "expected_article_count": 2,
            "source_artifacts": [{
                "path": "official.pdf", "official_url": "https://example.gov.vn/law.pdf",
                "sha256": _hash(artifact), "media_type": "application/pdf", "page_count": 1,
            }],
        },
        "provisions": [
            {"id": "law-test-art-1", "level": "article", "number": "1", "location": "Điều 1", "text": "Điều 1. Một"},
            {"id": "law-test-art-2", "level": "article", "number": "2", "location": "Điều 2", "text": "Điều 2. Hai"},
        ],
    }
    path = tmp_path / "source-pack.json"
    path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

    report = build_report(path)

    assert report["structural_checks_passed"] is True
    assert report["activation_eligible"] is False


def test_missing_article_breaks_structural_check(tmp_path):
    path = tmp_path / "source-pack.json"
    path.write_text(json.dumps({
        "document": {
            "id": "broken", "title": "Broken", "number": "X", "authority": "X",
            "official_url": "https://example.gov.vn/x", "content_hash": "0" * 64,
            "effective_from": "2024-01-01", "legal_status": "effective",
            "jurisdiction": "Vietnam", "version": "1", "expected_article_count": 2,
        },
        "provisions": [{"id": "broken-1", "level": "article", "number": "1", "location": "Điều 1", "text": "Nội dung"}],
    }), encoding="utf-8")

    report = build_report(path)

    assert report["checks"]["article_sequence_complete"] is False
    assert report["structural_checks_passed"] is False
