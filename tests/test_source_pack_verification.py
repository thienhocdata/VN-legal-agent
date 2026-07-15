import hashlib
import json
from pathlib import Path

from scripts.build_full_text_pack import ARTICLE_RE, select_article_matches
from scripts.promote_verified_pack import preflight
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


def test_article_selector_ignores_restarted_appendix_sequence():
    text = "Điều 1. Một\nĐiều 2. Hai\nĐiều 3. Ba\nĐiều 1. Mẫu\nĐiều 2. Mẫu"
    matches = list(ARTICLE_RE.finditer(text))

    selected = select_article_matches(matches, 3, "first_complete_sequence")

    assert [int(item.group(1)) for item in selected] == [1, 2, 3]


def test_article_selector_accepts_explicit_repealed_article_gaps():
    text = "Điều 1. Một\nĐiều 2. Hai\nĐiều 4. Bốn\nĐiều 1. Luật sửa đổi"
    matches = list(ARTICLE_RE.finditer(text))

    selected = select_article_matches(
        matches,
        3,
        "first_complete_sequence",
        [1, 2, 4],
    )

    assert [int(item.group(1)) for item in selected] == [1, 2, 4]


def test_activation_preflight_rejects_unresolved_nested_duplicates(tmp_path):
    artifact = tmp_path / "official.pdf"
    artifact.write_bytes(b"%PDF-official")
    artifact_hash = _hash(artifact)
    document = {
        "id": "law-test", "official_url": "https://example.gov.vn/law",
        "effective_from": "2024-01-01", "effective_to": None,
        "legal_status": "effective", "source_artifacts": [{
            "path": "official.pdf", "official_url": "https://example.gov.vn/law.pdf",
            "sha256": artifact_hash, "page_count": 1,
        }],
    }
    (tmp_path / "source-pack.json").write_text(json.dumps({
        "document": document, "relationships": [],
    }), encoding="utf-8")
    (tmp_path / "source-manifest.json").write_text(json.dumps({
        "document": {"id": "law-test"},
    }), encoding="utf-8")
    (tmp_path / "acquisition-record.json").write_text(json.dumps({
        "document_id": "law-test", "source_page_url": "https://example.gov.vn/law",
        "verification_status": "artifact_visual_verified_text_unverified",
        "artifacts": [{
            "path": "official.pdf", "official_url": "https://example.gov.vn/law.pdf",
            "sha256": artifact_hash, "page_count": 1,
        }],
    }), encoding="utf-8")
    (tmp_path / "visual-qa.json").write_text(json.dumps({
        "document_id": "law-test", "visual_checks_passed": True,
        "checks": {"identity": True, "readable": True},
    }), encoding="utf-8")
    (tmp_path / "integrity-report.json").write_text(json.dumps({
        "document_id": "law-test", "structural_checks_passed": True,
        "metrics": {"candidate_duplicate_nested_locations": 1},
    }), encoding="utf-8")

    try:
        preflight(tmp_path, "2026-07-15")
    except ValueError as exc:
        assert "Duplicate nested provision" in str(exc)
    else:
        raise AssertionError("Activation preflight accepted unresolved nested duplicates")
