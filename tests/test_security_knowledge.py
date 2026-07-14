import hashlib

from app.auth import issue_api_key
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
        con.execute("""INSERT INTO legal_documents VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""", (
            "law-reviewed", "Reviewed land rule", "01/2025/X", "Test authority",
            "https://example.gov.vn/law", digest, "2025-01-01", "2025-02-01", None,
            "effective", "Vietnam", None, "1.0",
        ))
        con.execute("INSERT INTO legal_provisions VALUES(?,?,?,?,?)", (
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
    assert "forbids demo-source fallback" in gap


def test_hcm_aliases_are_normalized_without_neighbor_leakage():
    assert normalize_locality("Sài Gòn") == ("TP. Hồ Chí Minh", True)
    assert normalize_locality("TPHCM") == ("TP. Hồ Chí Minh", True)
    assert normalize_locality("Đồng Nai") == ("Đồng Nai", False)
