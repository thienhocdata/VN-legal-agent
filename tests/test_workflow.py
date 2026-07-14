def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["legal_coverage"] == "demo_allowed"


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
    assert result.json()["status"] == "analysis_ready"

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
    assert data["status"] == "review_required"
    assert "Nhận định ban đầu" in data["answer"]
    assert data["citations"]
    messages = client.get(f"/api/v1/cases/{data['case_id']}/messages")
    assert [m["role"] for m in messages.json()] == ["user", "assistant"]


def test_chat_asks_one_material_question_at_a_time(client):
    first = client.post("/api/v1/chat", json={"message": "Tôi muốn bán một thửa đất."}).json()
    assert first["status"] == "intake_in_progress"
    assert "tỉnh hoặc thành phố" in first["answer"]
    second = client.post("/api/v1/chat", json={"case_id": first["case_id"], "message": "TP.HCM"}).json()
    assert "diễn ra vào ngày nào" in second["answer"]


def test_chat_answers_interruption_instead_of_repeating_pending_question(client):
    first = client.post("/api/v1/chat", json={
        "message": "Tôi muốn kiểm tra điều kiện chuyển nhượng một thửa đất tại TP.HCM."
    }).json()
    assert "diễn ra vào ngày nào" in first["answer"]

    definition = client.post("/api/v1/chat", json={
        "case_id": first["case_id"], "message": "Tách thửa là gì?"
    }).json()
    assert definition["status"] == "conversation"
    assert "Tách thửa" in definition["answer"]
    assert "diễn ra vào ngày nào" not in definition["answer"]

    topic_change = client.post("/api/v1/chat", json={
        "case_id": first["case_id"], "message": "Bạn có thể trả lời nội dung khác không?"
    }).json()
    assert topic_change["status"] == "conversation"
    assert "câu hoàn toàn khác" in topic_change["answer"]
    assert "diễn ra vào ngày nào" not in topic_change["answer"]


def test_chat_ui_is_single_conversation_and_scrollable(client):
    html = client.get("/").text
    css = client.get("/static/styles.css").text
    assert "Bạn cần hỗ trợ gì?" in html
    assert 'window.location.protocol === "file:"' in html
    assert 'http://127.0.0.1:8000/' in html
    assert "sidebar" not in html
    assert "id=\"menu\"" not in html
    assert ".conversation{min-height:0;overflow-y:auto" in css
