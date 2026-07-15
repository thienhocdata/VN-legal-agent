def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["legal_coverage"] == "governed_only"
    assert response.json()["ai_chat"]["mode"] == "unavailable"


def test_end_to_end_case_workflow(client, case):
    case_id = case["id"]
    result = client.post(f"/api/v1/cases/{case_id}/intake", json={
        "text": "Tôi muốn sang tên đất đã có sổ đỏ và hiện không có tranh chấp.",
        "actor_id": "user-1", "actor_role": "case_participant",
    })
    assert result.status_code == 200
    assert any(f["key"] == "transfer_mentioned" for f in result.json()["facts"])

    result = client.post(f"/api/v1/cases/{case_id}/context", json={
        "relevant_date": "2026-07-14", "locality": "TP. Hồ Chí Minh"
    })
    assert result.json()["status"] == "research_ready"

    result = client.post(f"/api/v1/cases/{case_id}/research", json={
        "query": "điều kiện chuyển nhượng giấy chứng nhận tranh chấp"
    })
    assert result.status_code == 200
    assert result.json()["status"] == "review_required"

    result = client.post(f"/api/v1/cases/{case_id}/analyze")
    assert result.status_code == 200
    data = result.json()
    assert data["status"] == "review_required"
    assert any(a["type"] == "evidence_map" for a in data["artifacts"])
    assert any(a["type"] == "action_plan" for a in data["artifacts"])

    reviewer_key = _key("lawyer-1", "demo", "professional_reviewer")
    result = client.post(f"/api/v1/cases/{case_id}/review", json={
        "actor_id": "lawyer-1", "actor_role": "professional_reviewer",
        "decision": "approved", "rationale": "Demo workflow reviewed."
    }, headers={"X-API-Key": reviewer_key})
    assert result.status_code == 200
    assert result.json()["status"] == "action_ready"
    assert len(client.get(f"/api/v1/cases/{case_id}/audit", headers={"X-API-Key": reviewer_key}).json()) >= 6


def test_research_requires_resolved_context(client, case):
    response = client.post(f"/api/v1/cases/{case['id']}/research", json={"query": "điều kiện chuyển nhượng"})
    assert response.status_code == 409


def test_agent_inference_cannot_be_auto_confirmed(client, case):
    # A participant cannot label their own input as an Agent inference.
    added = client.post(f"/api/v1/cases/{case['id']}/facts", json={
        "key": "possible_dispute", "value": True, "provenance": "agent_inferred", "actor_id": "agent"
    }).json()
    fact = next(f for f in added["facts"] if f["key"] == "possible_dispute")
    assert fact["provenance"] == "user_provided"
    # Internal Agent inference remains unconfirmed until an explicit actor action.
    import app.main as main
    from app.models import FactCreate, Provenance
    added = main.service.add_fact(case["id"], FactCreate(key="agent_hypothesis", value=True, provenance=Provenance.AGENT_INFERRED, actor_id="agent"))
    fact = next(f for f in added["facts"] if f["key"] == "agent_hypothesis")
    assert fact["provenance"] == "agent_inferred"
    confirmed = client.post(f"/api/v1/cases/{case['id']}/facts/{fact['id']}/confirm", json={
        "actor_id": "user-1", "actor_role": "case_participant"
    })
    assert confirmed.status_code == 200
    assert confirmed.json()["facts"][-1]["provenance"] == "user_confirmed"


def test_staff_cannot_confirm_fact(client, case):
    fact = case["facts"][0]
    response = client.post(f"/api/v1/cases/{case['id']}/facts/{fact['id']}/confirm", json={
        "actor_id": "staff-1", "actor_role": "case_staff"
    }, headers={"X-API-Key": _key("staff-1", "demo", "case_staff")})
    assert response.status_code == 403


def _key(actor, tenant, role):
    import app.main as main
    from app.auth import issue_api_key
    from app.models import Role

    main.auth.required = True
    return issue_api_key(main.db, actor, tenant, Role(role))


def test_tenant_isolation_hides_case(client, case):
    import app.main as main
    from app.auth import issue_api_key
    from app.models import Role

    other_key = issue_api_key(main.db, "other-user", "other", Role.CASE_PARTICIPANT)
    main.auth.required = True
    response = client.get(f"/api/v1/cases/{case['id']}", headers={"X-API-Key": other_key})
    assert response.status_code == 404


def test_fact_change_marks_artifacts_stale(client, case):
    case_id = case["id"]
    client.post(f"/api/v1/cases/{case_id}/clarify")
    response = client.post(f"/api/v1/cases/{case_id}/facts", json={
        "key": "locality", "value": "Hà Nội", "provenance": "user_provided", "actor_id": "user-1"
    })
    assert response.status_code == 200
    assert all(a["stale"] for a in response.json()["artifacts"])


def test_chat_first_flow_creates_hidden_case_and_answers(client):
    response = client.post("/api/v1/chat", json={
        "message": "Tôi muốn sang tên đất tại TPHCM ngày 14/07/2026, đã có sổ đỏ và không có tranh chấp."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"].startswith("case_")
    assert data["status"] == "ai_unavailable"
    assert "chưa được kết nối" in data["answer"]
    assert data["citations"] == []
    messages = client.get(f"/api/v1/cases/{data['case_id']}/messages")
    assert [m["role"] for m in messages.json()] == ["user", "assistant"]


def test_chat_asks_one_material_question_at_a_time(client):
    first = client.post("/api/v1/chat", json={"message": "Tôi muốn bán một thửa đất."}).json()
    assert first["status"] == "ai_unavailable"
    assert "chưa được kết nối" in first["answer"]
    second = client.post("/api/v1/chat", json={"case_id": first["case_id"], "message": "TP.HCM"}).json()
    assert second["status"] == "ai_unavailable"


def test_chat_answers_interruption_instead_of_repeating_pending_question(client):
    first = client.post("/api/v1/chat", json={
        "message": "Tôi muốn kiểm tra điều kiện chuyển nhượng một thửa đất tại TP.HCM."
    }).json()
    assert first["status"] == "ai_unavailable"

    definition = client.post("/api/v1/chat", json={
        "case_id": first["case_id"], "message": "Tách thửa là gì?"
    }).json()
    assert definition["status"] == "ai_unavailable"

    topic_change = client.post("/api/v1/chat", json={
        "case_id": first["case_id"], "message": "Bạn có thể trả lời nội dung khác không?"
    }).json()
    assert topic_change["status"] == "ai_unavailable"


def test_chat_ui_is_single_conversation_and_scrollable(client):
    html = client.get("/").text
    css = client.get("/static/styles.css").text
    assert "Bạn cần hỗ trợ gì?" in html
    assert 'window.location.protocol === "file:"' in html
    assert 'http://127.0.0.1:8000/' in html
    assert "sidebar" not in html
    assert "id=\"menu\"" not in html
    assert "data-prompt" not in html
    assert "Giải thích tách thửa" not in html
    assert "Georgia" not in css
    assert ".conversation{min-height:0;overflow-y:auto" in css


def test_configured_ai_handles_typo_as_conversation(client):
    import app.main as main
    from app.legal_ai import LegalAIResult

    class FakeLegalAI:
        available = True
        captured = None

        @staticmethod
        def status():
            return {"mode": "model", "configured": True, "model": "test-legal-model", "configuration_error": None}

        def generate(self, **kwargs):
            self.captured = kwargs
            return LegalAIResult(
                answer="Mình hiểu bạn đang hỏi về tách thửa tại TP.HCM.",
                suggestions=["Cho mình biết diện tích thửa đất"],
                model="test-legal-model",
            )

    fake = FakeLegalAI()
    main.service = main.LegalCaseService(main.db, legal_ai=fake)
    response = client.post("/api/v1/chat", json={"message": "tahc thua o tphcm co dc ko?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "conversation"
    assert "tách thửa" in data["answer"]
    assert fake.captured["history"][-1]["content"] == "tahc thua o tphcm co dc ko?"
    assert "case_purpose" not in fake.captured["facts"]


def test_context_extraction_accepts_missing_accents_and_punctuation(client):
    response = client.post("/api/v1/chat", json={
        "message": "Dat nay ko, co tranh chap; ko!!! the chap; da, co so do."
    }).json()
    case_data = client.get(f"/api/v1/cases/{response['case_id']}").json()
    latest = {fact["key"]: fact["value"] for fact in case_data["facts"]}
    assert latest["dispute_status"] is False
    assert latest["mortgage_status"] is False
    assert latest["certificate_status"] is True


def test_chua_co_tranh_chap_is_recorded_as_reported_absent(client):
    for message in ("Chưa có tranh chấp gì cả.", "chua co tranh chap gi ca"):
        response = client.post("/api/v1/chat", json={"message": message}).json()
        case_data = client.get(f"/api/v1/cases/{response['case_id']}").json()
        latest = {fact["key"]: fact["value"] for fact in case_data["facts"]}
        assert latest["dispute_status"] is False
        assert latest["dispute_report_status"] == "reported_absent"


def test_intake_does_not_flag_chua_co_tranh_chap_as_positive(client, case):
    result = client.post(f"/api/v1/cases/{case['id']}/intake", json={
        "text": "Thửa đất chưa có tranh chấp gì cả.",
        "actor_id": "user-1", "actor_role": "case_participant",
    })
    assert result.status_code == 200
    keys = {fact["key"] for fact in result.json()["facts"]}
    assert "dispute_mentioned" not in keys


def test_status_question_is_not_recorded_as_a_confirmed_case_fact(client):
    response = client.post("/api/v1/chat", json={
        "message": "Dat co tranh chap khong? Co dang the chap ko?"
    }).json()
    case_data = client.get(f"/api/v1/cases/{response['case_id']}").json()
    keys = {fact["key"] for fact in case_data["facts"]}
    assert "dispute_status" not in keys
    assert "mortgage_status" not in keys


def test_multiple_dated_events_keep_separate_timeline_entries(client):
    response = client.post("/api/v1/chat", json={
        "message": "Dat coc ngay 15/06/2024, cong chung ngay 20/08/2024 va sang ten 01/09/2024."
    }).json()
    case_data = client.get(f"/api/v1/cases/{response['case_id']}").json()
    timeline = next(
        fact["value"] for fact in reversed(case_data["facts"])
        if fact["key"] == "event_timeline"
    )
    assert [(item["type"], item["date"]) for item in timeline] == [
        ("deposit_contract", "2024-06-15"),
        ("notarization", "2024-08-20"),
        ("registration", "2024-09-01"),
    ]
    assert not any(fact["key"] == "relevant_date" for fact in case_data["facts"])


def test_ai_quota_failure_returns_short_overload_message_without_fake_answer(client):
    import app.main as main
    from app.legal_ai import LegalAIError

    class FailingLegalAI:
        available = True

        @staticmethod
        def status():
            return {"mode": "model", "configured": True, "model": "test-model", "configuration_error": None}

        @staticmethod
        def generate(**_):
            raise LegalAIError("Model request failed", code="insufficient_quota")

    main.service = main.LegalCaseService(main.db, legal_ai=FailingLegalAI())
    response = client.post("/api/v1/chat", json={"message": "Tách thửa là gì?"})
    assert response.status_code == 200
    assert response.json()["status"] == "ai_unavailable"
    assert "tạm quá tải" in response.json()["answer"]
    assert "Tách thửa là" not in response.json()["answer"]


def test_small_talk_uses_model_and_does_not_expose_legal_audit(client):
    import app.main as main

    class SmallTalkLegalAI:
        available = True
        called = 0

        @staticmethod
        def status():
            return {"mode": "model", "configured": True, "model": "test-model", "configuration_error": None}

        @staticmethod
        def generate(**_):
            from app.legal_ai import LegalAIResult
            SmallTalkLegalAI.called += 1
            return LegalAIResult(answer="Chào bạn, mình có thể hỗ trợ gì?", suggestions=[], model="test")

    main.service = main.LegalCaseService(main.db, legal_ai=SmallTalkLegalAI())
    response = client.post("/api/v1/chat", json={"message": "alo"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "conversation"
    assert data["answer"].startswith("Chào bạn")
    assert "Dữ kiện" not in data["answer"]
    assert "CHƯA THỂ KẾT LUẬN" not in data["answer"]
    assert data["citations"] == []
    assert data["suggestions"] == []
    assert SmallTalkLegalAI.called == 1
