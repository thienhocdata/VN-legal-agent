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
