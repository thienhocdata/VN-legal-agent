import hashlib
from pathlib import Path

from app.auth import issue_api_key
from app.database import Database
from app.knowledge import KnowledgeRepository
from app.models import Role
from app.coverage import normalize_locality


def test_authentication_required_rejects_anonymous(client):
    import app.main as main
    main.auth.required = True
    assert client.get("/api/v1/cases").status_code == 401


def test_authenticated_tenant_is_taken_from_key(client):
    import app.main as main
    key = issue_api_key(main.db, "staff-1", "tenant-a", Role.CASE_STAFF)
    main.auth.required = True
    created = client.post("/api/v1/cases", headers={"X-API-Key": key}, json={
        "purpose": "Kiểm tra giao dịch", "tenant_id": "spoofed", "actor_id": "spoofed", "actor_role": "professional_reviewer"
    }).json()
    assert created["tenant_id"] == "tenant-a"
    assert created["facts"][0]["actor_id"] == "staff-1"
    assert created["facts"][0]["provenance"] == "staff_entered"


def test_governed_source_resolves_temporal_applicability(client):
    import app.main as main
    digest = hashlib.sha256(b"reviewed-source").hexdigest()
    with main.db.connect() as con:
        con.execute("""INSERT INTO legal_documents
        (id,title,number,authority,official_url,content_hash,issued_date,effective_from,
         effective_to,legal_status,jurisdiction,locality,version,completeness_status,imported_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""", (
            "law-reviewed", "Reviewed land rule", "01/2025/X", "Test authority",
            "https://example.gov.vn/law", digest, "2025-01-01", "2025-02-01", None,
            "effective", "Vietnam", None, "1.0", "full_text_verified",
        ))
        con.execute(
            """UPDATE legal_documents SET artifact_integrity_status='verified',
            runtime_activation_status='active' WHERE id='law-reviewed'"""
        )
        con.execute("""INSERT INTO legal_provisions
        (id,document_id,location,text,keywords) VALUES(?,?,?,?,?)""", (
            "law-reviewed-art-1", "law-reviewed", "Article 1", "Điều kiện chuyển nhượng quyền sử dụng đất", '["chuyển nhượng"]'
        ))
    repo = KnowledgeRepository(main.db, allow_demo=False)
    hits, gap = repo.search("điều kiện chuyển nhượng", {"relevant_date": "2026-07-14", "locality": "Hà Nội"})
    assert gap is None
    assert hits[0]["applicability"] == "candidate"
    assert hits[0]["snapshot"].startswith("law-reviewed:1.0:")


def test_pilot_knowledge_fails_closed_without_match(client):
    import app.main as main
    hits, gap = KnowledgeRepository(main.db, allow_demo=False).search("không có nguồn", {"relevant_date": "2026-01-01"})
    assert hits == []
    assert "không cho phép dùng dữ liệu demo" in gap


def test_unverified_full_text_is_never_retrieved(client):
    import app.main as main
    digest = hashlib.sha256(b"unverified-source").hexdigest()
    with main.db.connect() as con:
        con.execute("""INSERT INTO legal_documents
        (id,title,number,authority,official_url,content_hash,effective_from,
         legal_status,jurisdiction,version,completeness_status,imported_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""", (
            "law-unverified", "Nguồn chưa kiểm chứng", "02/TEST", "Test authority",
            "https://example.gov.vn/unverified", digest, "2024-01-01",
            "effective", "Vietnam", "original", "full_text_unverified",
        ))
        con.execute("""INSERT INTO legal_provisions
        (id,document_id,location,text,keywords) VALUES(?,?,?,?,?)""", (
            "law-unverified-art-1", "law-unverified", "Điều 1",
            "Quy định bí mật chỉ có trong nguồn chưa kiểm chứng", '["bí mật"]'
        ))
    hits, gap = KnowledgeRepository(main.db, allow_demo=False).search(
        "quy định bí mật", {"relevant_date": "2026-07-14", "locality": "TP. Hồ Chí Minh"}
    )
    assert hits == []
    assert "toàn văn đã kiểm chứng" in gap


def test_hcm_aliases_are_normalized_without_neighbor_leakage():
    assert normalize_locality("Sài Gòn") == ("TP. Hồ Chí Minh", True)
    assert normalize_locality("TPHCM") == ("TP. Hồ Chí Minh", True)
    assert normalize_locality("Đồng Nai") == ("Đồng Nai", False)


def test_search_index_refreshes_when_corpus_revision_changes(tmp_path: Path):
    database = Database(tmp_path / "revision.db")
    repository = KnowledgeRepository(database, allow_demo=False)
    hits, _ = repository.search(
        "quyền chuyển nhượng",
        {"relevant_date": "2026-07-15", "locality": "TP. Hồ Chí Minh"},
    )
    assert hits == []

    with database.connect() as con:
        con.execute(
                """INSERT INTO legal_documents
                (id,title,number,authority,official_url,content_hash,effective_from,
                 legal_status,jurisdiction,version,imported_at,completeness_status,
                 artifact_integrity_status,runtime_activation_status)
                VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'),'full_text_verified','verified','active')""",
            (
                "revision-law", "Luật kiểm thử", "01/TEST", "Quốc hội",
                "https://example.gov.vn/revision", "a" * 64, "2024-01-01",
                "effective", "Vietnam", "v1",
            ),
        )
        con.execute(
            """INSERT INTO legal_provisions
            (id,document_id,location,text,keywords,level,legal_status)
            VALUES(?,?,?,?,?,'article','effective')""",
            (
                "revision-law-art-1", "revision-law", "Điều 1",
                "Quyền chuyển nhượng quyền sử dụng đất", "[]",
            ),
        )
        con.execute(
            """UPDATE corpus_runtime_state
            SET revision=revision+1,activation_status='active' WHERE singleton=1"""
        )

    refreshed, _ = repository.search(
        "quyền chuyển nhượng",
        {"relevant_date": "2026-07-15", "locality": "TP. Hồ Chí Minh"},
    )
    assert refreshed[0]["provision_id"] == "revision-law-art-1"


def test_issue_retrieval_deduplicates_document_article_evidence(tmp_path: Path):
    repository = KnowledgeRepository(Database(tmp_path / "dedup.db"), allow_demo=False)
    duplicate_article_hits = [
        {
            "source_id": "law-1", "provision_id": "law-1-art-10",
            "article_id": "law-1-art-10", "applicability": "candidate",
            "governance_status": "full_text_verified", "score": 20,
        },
        {
            "source_id": "law-1", "provision_id": "law-1-art-10-cl-1",
            "article_id": "law-1-art-10", "applicability": "candidate",
            "governance_status": "full_text_verified", "score": 18,
        },
    ]
    repository.search = lambda _query, _context: (duplicate_article_hits, None)  # type: ignore[method-assign]

    hits, notice = repository.search_by_issues(
        "điều kiện chuyển nhượng", {"relevant_date": "2026-07-15"}
    )

    assert notice is None
    assert len(hits) == 1
    assert hits[0]["source_id"] == "law-1"
    assert hits[0]["article_id"] == "law-1-art-10"
