from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.decision_audit import (
    AUDIT_HEADINGS,
    requires_decision_audit,
    safe_inconclusive_answer,
    validate_decision_answer,
)
from app.legal_ai import LegalAI
from app.database import Database
from app.knowledge import KnowledgeRepository


def verified_source() -> dict:
    return {
        "source_id": "law-test",
        "title": "Luật kiểm thử",
        "location": "Điều 1 khoản 1",
        "effective_from": "2024-01-01",
        "effective_to": None,
        "legal_status": "effective",
        "document_type": "law",
        "locality": None,
        "applicability": "candidate",
        "governance_status": "full_text_verified",
        "summary": "Điều kiện kiểm thử.",
    }


def test_decision_request_is_distinguished_from_definition():
    assert requires_decision_audit("Tôi muốn sang tên đất tại TP.HCM")
    assert requires_decision_audit("Thửa đất này có tách được không?")
    assert not requires_decision_audit("Tách thửa là gì?")


def test_safe_answer_always_exposes_all_six_gates_and_inconclusive_verdict():
    answer = safe_inconclusive_answer(
        facts={"locality": "TP. Hồ Chí Minh"},
        sources=[],
        source_notice="Chưa có nguồn toàn văn đã kiểm chứng.",
    )
    assert all(heading in answer for heading in AUDIT_HEADINGS)
    assert "**CHƯA THỂ KẾT LUẬN**" in answer
    valid, errors = validate_decision_answer(answer, [])
    assert valid, errors


def test_conclusive_verdict_is_rejected_without_direct_governed_evidence():
    answer = "\n\n".join([
        "**1. Dữ kiện**\n- Đủ.",
        "**2. Ngoại lệ**\n- Không có.",
        "**3. Hiệu lực**\n- Đang có hiệu lực.",
        "**4. Văn bản liên ngành**\n- Đã kiểm tra.",
        "**5. Kết luận**\n**ĐƯỢC**",
        "**6. Bằng chứng trực tiếp**\n- Không nêu nguồn.",
    ])
    valid, errors = validate_decision_answer(answer, [])
    assert not valid
    assert "conclusive_verdict_without_direct_evidence" in errors


def test_decision_without_verified_corpus_skips_model_and_returns_safe_contract():
    settings = Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=True, ai_model="test-model",
    )
    ai = LegalAI(settings)

    class MustNotRun:
        @staticmethod
        def create(**_):
            raise AssertionError("Provider must not be called without governed evidence")

    ai.client = SimpleNamespace(responses=MustNotRun())
    result = ai.generate(
        history=[{"role": "user", "content": "Tôi muốn sang tên đất tại TP.HCM"}],
        facts={"locality": "TP. Hồ Chí Minh"},
        sources=[],
        source_notice="Thiếu corpus.",
    )
    assert result.response_status == "corpus_gap"
    assert result.decision_audit is True
    assert "**CHƯA THỂ KẾT LUẬN**" in result.answer


def test_decision_prompt_contains_contract_and_accepts_evidence_linked_output():
    settings = Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=False, ai_model="test-model",
    )
    ai = LegalAI(settings)
    answer = "\n\n".join([
        "**1. Dữ kiện**\n- Đã có dữ kiện cần thiết.",
        "**2. Ngoại lệ**\n- Đã kiểm tra ngoại lệ trong phạm vi nguồn.",
        "**3. Hiệu lực**\n- [Nguồn 1] áp dụng tại ngày sự kiện.",
        "**4. Văn bản liên ngành**\n- Chưa phát sinh nhóm khác trong tình huống kiểm thử.",
        "**5. Kết luận**\n**ĐƯỢC**",
        "**6. Bằng chứng trực tiếp**\n- [Nguồn 1], Điều 1 khoản 1 hỗ trợ trực tiếp kết luận.",
    ])

    class FakeResponses:
        request = None

        def create(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(output_text=answer)

    responses = FakeResponses()
    ai.client = SimpleNamespace(responses=responses)
    result = ai.generate(
        history=[{"role": "user", "content": "Giao dịch này có được thực hiện không?"}],
        facts={"locality": "TP. Hồ Chí Minh", "relevant_date": "2026-07-15"},
        sources=[verified_source()],
        source_notice=None,
    )
    assert result.answer == answer
    assert result.decision_audit is True
    assert "HỢP ĐỒNG OUTPUT CHO CÂU HỎI CẦN RA QUYẾT ĐỊNH" in responses.request["instructions"]


def test_historical_rule_is_selected_by_event_date_not_only_current_status(tmp_path):
    database = Database(tmp_path / "history.db")
    with database.connect() as con:
        con.execute(
            """INSERT INTO legal_documents
            (id,title,number,authority,official_url,content_hash,effective_from,effective_to,
             legal_status,jurisdiction,version,imported_at,completeness_status,document_type)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "old-law", "Luật đất đai cũ", "OLD/TEST", "Quốc hội",
                "https://example.gov.vn/old", "a" * 64, "2014-07-01", "2024-07-31",
                "repealed", "Vietnam", "original", "2026-07-15T00:00:00Z",
                "full_text_verified", "law",
            ),
        )
        con.execute(
            """INSERT INTO legal_provisions
            (id,document_id,location,text,keywords,legal_status)
            VALUES(?,?,?,?,?,?)""",
            (
                "old-law-art-1", "old-law", "Điều 1",
                "Điều kiện chuyển nhượng quyền sử dụng đất", "chuyển nhượng", "effective",
            ),
        )

    repository = KnowledgeRepository(database, allow_demo=False)
    historical, _ = repository.search(
        "chuyển nhượng", {"relevant_date": "2020-01-01", "locality": "TP. Hồ Chí Minh"}
    )
    current, _ = repository.search(
        "chuyển nhượng", {"relevant_date": "2026-07-15", "locality": "TP. Hồ Chí Minh"}
    )
    assert historical[0]["applicability"] == "candidate"
    assert current[0]["applicability"] == "not_applicable"


def test_unresolved_repealed_provision_cannot_support_a_conclusion(tmp_path):
    database = Database(tmp_path / "provision-status.db")
    with database.connect() as con:
        con.execute(
            """INSERT INTO legal_documents
            (id,title,number,authority,official_url,content_hash,effective_from,
             legal_status,jurisdiction,version,imported_at,completeness_status,document_type)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "mixed-law", "Luật có điều khoản bị bãi bỏ", "MIXED/TEST", "Quốc hội",
                "https://example.gov.vn/mixed", "b" * 64, "2024-01-01", "effective",
                "Vietnam", "original", "2026-07-15T00:00:00Z", "full_text_verified", "law",
            ),
        )
        con.execute(
            """INSERT INTO legal_provisions
            (id,document_id,location,text,keywords,legal_status)
            VALUES(?,?,?,?,?,?)""",
            (
                "mixed-law-art-1", "mixed-law", "Điều 1",
                "Điều kiện chuyển nhượng quyền sử dụng đất", "chuyển nhượng", "repealed",
            ),
        )

    hits, _ = KnowledgeRepository(database, allow_demo=False).search(
        "chuyển nhượng", {"relevant_date": "2026-07-15", "locality": "TP. Hồ Chí Minh"}
    )
    assert hits[0]["applicability"] == "not_applicable"
