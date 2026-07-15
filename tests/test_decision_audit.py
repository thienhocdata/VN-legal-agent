
import json
from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.decision_audit import (
    compose_structured_user_answer,
    requires_decision_audit,
    validate_decision_json,
)
from app.legal_ai import LegalAI, ProviderRuntime
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
    assert requires_decision_audit("dat nay, co sang ten dc ko???")
    assert not requires_decision_audit("Tách thửa là gì?")


def test_structured_audit_keeps_separate_verdicts_and_is_not_exposed_to_user():
    source = verified_source()
    payload = {
        "issues": [
            {
                "issue": "Hiệu lực đặt cọc", "status": "partially_supported",
                "finding": "Có căn cứ một phần.", "known_facts": ["Đã có ngày đặt cọc"],
                "missing_facts": ["Nội dung hợp đồng"], "exceptions": [],
                "effectiveness_check": "Đã đối chiếu ngày.",
                "interdisciplinary_checks": ["Dân sự"],
                "evidence": [{"source": 1, "location": "Điều 1", "supports": "điều kiện chung"}],
            },
            {
                "issue": "Đăng ký sang tên", "status": "insufficient_basis",
                "finding": "Chưa đủ hồ sơ để kết luận.", "known_facts": [],
                "missing_facts": ["Tình trạng thế chấp"], "exceptions": ["Chưa kiểm tra ngoại lệ"],
                "effectiveness_check": "Chưa có ngày đăng ký.",
                "interdisciplinary_checks": ["Đăng ký đất đai chưa đủ"], "evidence": [],
            },
        ],
        "overall_caution": "Chỉ là nhận định sơ bộ.",
        "follow_up_question": "Đất hiện có đang thế chấp không?",
    }
    raw = json.dumps(payload, ensure_ascii=False)
    valid, errors, parsed = validate_decision_json(raw, [source])
    assert valid, errors
    answer = compose_structured_user_answer(audit=parsed, sources=[source], source_notice=None)
    assert "Hiệu lực đặt cọc" in answer and "Đăng ký sang tên" in answer
    assert "partially_supported" not in answer and '"issues"' not in answer
    assert answer.count("Đất hiện có đang thế chấp không?") == 1


def test_decision_without_verified_corpus_calls_model_but_stays_inconclusive():
    settings = Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=True, ai_model="test-model",
    )
    ai = LegalAI(settings)

    payload = {
        "issues": [{
            "issue": "Sang tên quyền sử dụng đất",
            "status": "insufficient_basis",
            "finding": "Corpus hiện chưa có bằng chứng trực tiếp đủ để kết luận.",
            "known_facts": ["Địa phương do người dùng cung cấp: TP.HCM"],
            "missing_facts": ["Ngày giao dịch"],
            "exceptions": ["Chưa kiểm tra đủ ngoại lệ"],
            "effectiveness_check": "Chưa xác định được ngày áp dụng.",
            "interdisciplinary_checks": ["Chưa kiểm tra đủ"],
            "evidence": [],
        }],
        "overall_caution": "Chưa dùng trí nhớ mô hình thay cho nguồn.",
        "follow_up_question": "Giao dịch dự kiến diễn ra vào ngày nào?",
    }

    class Responses:
        called = 0
        def create(self, **_):
            self.called += 1
            return SimpleNamespace(output_text=json.dumps(payload, ensure_ascii=False), status="completed")

    responses = Responses()
    ai.providers = [ProviderRuntime("openai", "test", "responses", SimpleNamespace(responses=responses))]
    result = ai.generate(
        history=[{"role": "user", "content": "Tôi muốn sang tên đất tại TP.HCM"}],
        facts={"locality": "TP. Hồ Chí Minh"},
        sources=[],
        source_notice="Thiếu corpus.",
    )
    assert result.response_status == "conversation"
    assert result.decision_audit is True
    assert responses.called == 1
    assert result.generation_mode == "model"
    assert result.provider_called is True
    assert result.provider_model == "test"
    assert "insufficient_basis" in result.internal_audit
    assert "Chưa đủ căn cứ để kết luận" in result.answer


def test_decision_prompt_contains_contract_and_accepts_evidence_linked_output():
    settings = Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=False, ai_model="test-model",
    )
    ai = LegalAI(settings)
    payload = {
        "issues": [{
            "issue": "Điều kiện giao dịch",
            "status": "supported",
            "finding": "Giao dịch có căn cứ để tiếp tục trong phạm vi dữ kiện đã kiểm tra.",
            "known_facts": ["Địa phương và ngày đã có"],
            "missing_facts": [], "exceptions": [],
            "effectiveness_check": "Nguồn phù hợp ngày và địa phương.",
            "interdisciplinary_checks": ["Đã kiểm tra nguồn được cung cấp"],
            "evidence": [{"source": 1, "location": "Điều 1 khoản 1", "supports": "điều kiện trực tiếp"}],
        }],
        "overall_caution": "Kết luận chỉ trong phạm vi dữ kiện đã xác minh.",
        "follow_up_question": "",
    }
    answer = json.dumps(payload, ensure_ascii=False)

    class FakeResponses:
        request = None

        def create(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(output_text=answer, status="completed")

    responses = FakeResponses()
    ai.providers = [ProviderRuntime("openai", "test", "responses", SimpleNamespace(responses=responses))]
    result = ai.generate(
        history=[{"role": "user", "content": "Giao dịch này có được thực hiện không?"}],
        facts={"locality": "TP. Hồ Chí Minh", "relevant_date": "2026-07-15"},
        sources=[verified_source()],
        source_notice=None,
    )
    assert json.loads(result.internal_audit) == payload
    assert result.answer != answer
    assert "Căn cứ trực tiếp" in result.answer
    assert result.decision_audit is True
    assert "HỢP ĐỒNG OUTPUT NỘI BỘ CHO CÂU HỎI CẦN RA QUYẾT ĐỊNH" in responses.request["instructions"]


def test_current_question_replaces_old_case_purpose_in_internal_audit():
    settings = Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=False, ai_model="test-model",
    )
    ai = LegalAI(settings)
    current = "Tôi muốn sang tên thửa đất đang thế chấp tại TP.HCM"
    payload = {
        "issues": [{
            "issue": "Sang tên đất đang thế chấp", "status": "insufficient_basis",
            "finding": current, "known_facts": ["TP.HCM"],
            "missing_facts": ["Tình trạng chấp thuận của ngân hàng"],
            "exceptions": ["Chưa kiểm tra"], "effectiveness_check": "Chưa có ngày",
            "interdisciplinary_checks": ["Chưa đủ"], "evidence": [],
        }], "overall_caution": "", "follow_up_question": "",
    }
    class Responses:
        def create(self, **_):
            return SimpleNamespace(output_text=json.dumps(payload, ensure_ascii=False), status="completed")
    ai.providers = [ProviderRuntime("openai", "test", "responses", SimpleNamespace(responses=Responses()))]
    result = ai.generate(
        history=[
            {"role": "user", "content": "alo"},
            {"role": "assistant", "content": "Chào bạn"},
            {"role": "user", "content": current},
        ],
        question=current,
        facts={"case_purpose": "alo", "locality": "TP. Hồ Chí Minh"},
        sources=[],
        source_notice="Thiếu corpus.",
    )
    assert current in result.internal_audit
    assert '"finding": "alo"' not in result.internal_audit


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
        con.execute(
            """UPDATE legal_documents SET artifact_integrity_status='verified',
            runtime_activation_status='active' WHERE id='old-law'"""
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


def test_expired_rule_can_be_used_only_as_historical_comparison_evidence(tmp_path):
    database = Database(tmp_path / "historical-comparison.db")
    with database.connect() as con:
        con.execute(
            """INSERT INTO legal_documents
            (id,title,number,authority,official_url,content_hash,effective_from,effective_to,
             legal_status,jurisdiction,version,imported_at,completeness_status,document_type)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "land-law-2013", "Luật Đất đai 2013", "45/2013/QH13", "Quốc hội",
                "https://example.gov.vn/2013", "c" * 64, "2014-07-01", "2024-07-31",
                "expired", "Vietnam", "consolidated", "2026-07-15T00:00:00Z",
                "full_text_verified", "law",
            ),
        )
        con.execute(
            """INSERT INTO legal_provisions
            (id,document_id,location,text,keywords,legal_status)
            VALUES(?,?,?,?,?,?)""",
            (
                "land-law-2013-art-188", "land-law-2013", "Điều 188",
                "Điều kiện chuyển nhượng quyền sử dụng đất", "chuyển nhượng", "effective",
            ),
        )
        con.execute(
            """UPDATE legal_documents SET artifact_integrity_status='verified',
            runtime_activation_status='active' WHERE id='land-law-2013'"""
        )

    repository = KnowledgeRepository(database, allow_demo=False)
    comparison, _ = repository.search(
        "So sánh điều kiện chuyển nhượng theo Luật Đất đai 2013 và luật hiện hành",
        {"relevant_date": "2026-07-15", "locality": "TP. Hồ Chí Minh"},
    )
    ordinary, _ = repository.search(
        "Điều kiện chuyển nhượng hiện nay",
        {"relevant_date": "2026-07-15", "locality": "TP. Hồ Chí Minh"},
    )
    assert comparison[0]["applicability"] == "candidate"
    assert comparison[0]["evidence_role"] == "historical_reference"
    assert ordinary[0]["applicability"] == "not_applicable"


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
        con.execute(
            """UPDATE legal_documents SET artifact_integrity_status='verified',
            runtime_activation_status='active' WHERE id='mixed-law'"""
        )

    hits, _ = KnowledgeRepository(database, allow_demo=False).search(
        "chuyển nhượng", {"relevant_date": "2026-07-15", "locality": "TP. Hồ Chí Minh"}
    )
    assert hits[0]["applicability"] == "not_applicable"
