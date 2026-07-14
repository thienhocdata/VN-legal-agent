from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from .database import Database
from .knowledge import KnowledgeRepository
from .coverage import normalize_locality
from .models import CaseCreate, CaseStatus, ContextRequest, FactConfirm, FactCreate, Provenance, ResearchRequest, ReviewRequest, Role


def now() -> str:
    return datetime.now(UTC).isoformat()


class LegalCaseService:
    def __init__(self, db: Database, knowledge: KnowledgeRepository | None = None):
        self.db = db
        self.knowledge = knowledge or KnowledgeRepository(db, True)

    def audit(self, con, case_id: str, event: str, actor: str, payload: dict):
        con.execute("INSERT INTO audit_events(case_id,event_type,actor_id,payload,created_at) VALUES(?,?,?,?,?)", (case_id, event, actor, self.db.json(payload), now()))

    def create_case(self, req: CaseCreate) -> dict:
        case_id, ts = f"case_{uuid4().hex[:12]}", now()
        with self.db.connect() as con:
            con.execute("INSERT INTO cases VALUES(?,?,?,?,?,?,?,?)", (case_id, req.tenant_id, req.purpose, CaseStatus.INTAKE_IN_PROGRESS, 1, self.db.json(req.property_ids), ts, ts))
            self.audit(con, case_id, "case.created", req.actor_id, req.model_dump(mode="json"))
            self._insert_fact(con, case_id, FactCreate(key="case_purpose", value=req.purpose, provenance=Provenance.USER_PROVIDED if req.actor_role == Role.CASE_PARTICIPANT else Provenance.STAFF_ENTERED, actor_id=req.actor_id, source_id="case_create"))
        return self.get_case(case_id, req.tenant_id)

    def _case(self, con, case_id: str, tenant_id: str | None = None):
        row = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not row or (tenant_id and row["tenant_id"] != tenant_id):
            raise HTTPException(404, "Case not found")
        return row

    def get_case(self, case_id: str, tenant_id: str | None = None) -> dict:
        with self.db.connect() as con:
            case = dict(self._case(con, case_id, tenant_id))
            facts = [dict(r) for r in con.execute("SELECT * FROM facts WHERE case_id=? ORDER BY created_at", (case_id,))]
            artifacts = [dict(r) for r in con.execute("SELECT * FROM artifacts WHERE case_id=? ORDER BY created_at", (case_id,))]
        case["property_ids"] = json.loads(case["property_ids"])
        for f in facts: f["value"] = json.loads(f["value"])
        for a in artifacts:
            a["data"], a["stale"] = json.loads(a["data"]), bool(a["stale"])
        case["facts"], case["artifacts"] = facts, artifacts
        return case

    def list_cases(self, tenant_id: str) -> list[dict]:
        with self.db.connect() as con:
            rows = con.execute("SELECT * FROM cases WHERE tenant_id=? ORDER BY updated_at DESC", (tenant_id,)).fetchall()
        return [{**dict(r), "property_ids": json.loads(r["property_ids"])} for r in rows]

    def _insert_fact(self, con, case_id: str, fact: FactCreate, supersedes_id=None):
        fact_id = f"fact_{uuid4().hex[:12]}"
        con.execute("INSERT INTO facts VALUES(?,?,?,?,?,?,?,?,?,?)", (fact_id, case_id, fact.key, self.db.json(fact.value), fact.provenance, fact.actor_id, fact.source_id, fact.method, now(), supersedes_id))
        return fact_id

    def add_fact(self, case_id: str, fact: FactCreate) -> dict:
        if fact.provenance in {Provenance.USER_CONFIRMED, Provenance.PROFESSIONAL_CONFIRMED}:
            raise HTTPException(422, "Confirmed provenance requires the confirmation endpoint")
        with self.db.connect() as con:
            self._case(con, case_id)
            fact_id = self._insert_fact(con, case_id, fact)
            self._invalidate(con, case_id, "fact changed")
            self.audit(con, case_id, "fact.added", fact.actor_id, {"fact_id": fact_id, **fact.model_dump(mode="json")})
        return self.get_case(case_id)

    def intake(self, case_id: str, actor_id: str, role: Role, text: str) -> dict:
        source_id = f"utterance_{uuid4().hex[:10]}"
        provenance = Provenance.USER_PROVIDED if role == Role.CASE_PARTICIPANT else Provenance.STAFF_ENTERED
        candidates = {"narrative": text}
        for label, pattern in {
            "certificate_mentioned": r"sổ đỏ|sổ hồng|giấy chứng nhận",
            "transfer_mentioned": r"chuyển nhượng|mua bán|sang tên",
        }.items():
            if re.search(pattern, text, re.I): candidates[label] = True
        if re.search(r"tranh chấp|khởi kiện|khiếu nại", text, re.I) and not re.search(r"không (có )?(tranh chấp|khởi kiện|khiếu nại)", text, re.I):
            candidates["dispute_mentioned"] = True
        with self.db.connect() as con:
            self._case(con, case_id)
            for key, value in candidates.items():
                self._insert_fact(con, case_id, FactCreate(key=key, value=value, provenance=provenance, actor_id=actor_id, source_id=source_id, method="rule_based_intake"))
            self._invalidate(con, case_id, "intake changed")
            self.audit(con, case_id, "intake.recorded", actor_id, {"source_id": source_id, "text": text, "extracted_keys": list(candidates)})
        return self.clarify(case_id)

    def confirm_fact(self, case_id: str, fact_id: str, req: FactConfirm) -> dict:
        with self.db.connect() as con:
            self._case(con, case_id)
            old = con.execute("SELECT * FROM facts WHERE id=? AND case_id=?", (fact_id, case_id)).fetchone()
            if not old: raise HTTPException(404, "Fact not found")
            if req.actor_role == Role.PROFESSIONAL_REVIEWER:
                provenance = Provenance.PROFESSIONAL_CONFIRMED
            elif req.actor_role == Role.CASE_PARTICIPANT:
                provenance = Provenance.USER_CONFIRMED
            else:
                raise HTTPException(403, "Staff cannot create confirmed facts")
            value = req.value if req.value is not None else json.loads(old["value"])
            new_id = self._insert_fact(con, case_id, FactCreate(key=old["key"], value=value, provenance=provenance, actor_id=req.actor_id, source_id=fact_id, method="explicit_confirmation"), fact_id)
            self._invalidate(con, case_id, "fact confirmed")
            self.audit(con, case_id, "fact.confirmed", req.actor_id, {"prior_fact_id": fact_id, "fact_id": new_id, "provenance": provenance})
        return self.get_case(case_id)

    def _latest(self, con, case_id: str, key: str):
        row = con.execute("SELECT * FROM facts WHERE case_id=? AND key=? ORDER BY created_at DESC LIMIT 1", (case_id, key)).fetchone()
        return json.loads(row["value"]) if row else None

    def _artifact(self, con, case_id: str, type_: str, data: dict, status="current"):
        version = con.execute("SELECT COALESCE(MAX(version),0)+1 FROM artifacts WHERE case_id=? AND type=?", (case_id, type_)).fetchone()[0]
        con.execute("UPDATE artifacts SET stale=1,status='stale' WHERE case_id=? AND type=?", (case_id, type_))
        art_id = f"art_{uuid4().hex[:12]}"
        cv = con.execute("SELECT version FROM cases WHERE id=?", (case_id,)).fetchone()[0]
        con.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?)", (art_id, case_id, type_, version, status, self.db.json(data), cv, 0, now()))
        return art_id

    def _invalidate(self, con, case_id: str, reason: str):
        con.execute("UPDATE artifacts SET stale=1,status='stale' WHERE case_id=? AND stale=0", (case_id,))
        con.execute("UPDATE cases SET version=version+1,updated_at=? WHERE id=?", (now(), case_id))

    def clarify(self, case_id: str) -> dict:
        required = [("locality", "Thửa đất thuộc tỉnh/thành phố nào?"), ("relevant_date", "Giao dịch hoặc sự kiện pháp lý diễn ra vào ngày nào?"), ("certificate_status", "Hiện có Giấy chứng nhận hay chưa?"), ("dispute_status", "Đất có tranh chấp, khiếu nại hoặc khởi kiện không?")]
        with self.db.connect() as con:
            self._case(con, case_id)
            missing = [{"key": k, "question": q, "materiality": "blocking" if k in {"locality", "relevant_date"} else "material"} for k, q in required if self._latest(con, case_id, k) is None]
            issues = []
            if self._latest(con, case_id, "transfer_mentioned"): issues.append({"code": "land_transfer", "status": "active", "rationale": "Transfer intent was stated"})
            if self._latest(con, case_id, "dispute_mentioned"): issues.append({"code": "land_dispute", "status": "review_required", "rationale": "A dispute was mentioned"})
            self._artifact(con, case_id, "clarification", {"missing_facts": missing})
            self._artifact(con, case_id, "issue_map", {"issues": issues})
            status = CaseStatus.REVIEW_REQUIRED if any(i["status"] == "review_required" for i in issues) else CaseStatus.INTAKE_IN_PROGRESS
            con.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (status, now(), case_id))
        return self.get_case(case_id)

    def set_context(self, case_id: str, req: ContextRequest) -> dict:
        req.locality, locality_supported = normalize_locality(req.locality)
        unresolved = [k for k, v in {"relevant_date": req.relevant_date, "locality": req.locality}.items() if not v]
        local_verified = bool(req.locality and self.knowledge.has_locality(req.locality, req.relevant_date))
        data = {**req.model_dump(), "unresolved": unresolved, "locality_supported": locality_supported, "local_procedure_verified": local_verified}
        with self.db.connect() as con:
            self._case(con, case_id)
            self._artifact(con, case_id, "research_context", data, "blocked" if unresolved else "current")
            con.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (CaseStatus.INTAKE_IN_PROGRESS if unresolved else CaseStatus.RESEARCH_READY, now(), case_id))
            self.audit(con, case_id, "context.resolved", "system", data)
        return self.get_case(case_id)

    def research(self, case_id: str, req: ResearchRequest) -> dict:
        with self.db.connect() as con:
            self._case(con, case_id)
            ctxrow = con.execute("SELECT * FROM artifacts WHERE case_id=? AND type='research_context' AND stale=0 ORDER BY version DESC LIMIT 1", (case_id,)).fetchone()
            if not ctxrow or json.loads(ctxrow["data"])["unresolved"]:
                raise HTTPException(409, "Relevant date and locality must be resolved before research")
            ctx = json.loads(ctxrow["data"])
            hits, gap = self.knowledge.search(req.query, ctx)
            self._artifact(con, case_id, "research_session", {"query": req.query, "context": ctx, "results": hits, "research_gap": gap})
            con.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (CaseStatus.ANALYSIS_READY if hits else CaseStatus.REVIEW_REQUIRED, now(), case_id))
            self.audit(con, case_id, "research.completed", "system", {"query": req.query, "result_count": len(hits)})
        return self.get_case(case_id)

    def analyze(self, case_id: str) -> dict:
        with self.db.connect() as con:
            self._case(con, case_id)
            research = con.execute("SELECT * FROM artifacts WHERE case_id=? AND type='research_session' AND stale=0 ORDER BY version DESC LIMIT 1", (case_id,)).fetchone()
            if not research: raise HTTPException(409, "Current research is required")
            rd = json.loads(research["data"])
            facts = [dict(r) for r in con.execute("SELECT * FROM facts WHERE case_id=?", (case_id,))]
            fact_links = [{"fact_id": f["id"], "key": f["key"], "provenance": f["provenance"]} for f in facts]
            evidence = [{"source_id": r["source_id"], "source_version": r["snapshot"], "citation_location": r["location"], "applicability": r["applicability"]} for r in rd["results"]]
            high_risk = any(f["key"] == "dispute_mentioned" and json.loads(f["value"]) for f in facts)
            analysis = {
                "scope": "Demonstration only — not a final legal opinion",
                "conclusion": "The matter requires verification of statutory transfer conditions and local procedure before action.",
                "applicable_facts": fact_links,
                "legal_evidence": evidence,
                "uncertainty": {"facts": "medium", "source_coverage": "high", "locality": "high", "interpretation": "medium"},
                "limitations": [rd["research_gap"]] if rd["research_gap"] else [],
                "review_required": high_risk or True,
            }
            self._artifact(con, case_id, "evidence_map", {"proposition": analysis["conclusion"], "facts": fact_links, "rules": evidence})
            self._artifact(con, case_id, "legal_analysis", analysis, "review_required")
            plan = {"risks": ["Acting on incomplete or unverified legal information"], "steps": [
                {"order": 1, "actor": "case_participant", "action": "Confirm missing and conflicting case facts"},
                {"order": 2, "actor": "case_staff", "action": "Verify official national and locality-specific sources"},
                {"order": 3, "actor": "professional_reviewer", "action": "Review evidence-linked analysis before reliance"},
            ], "external_action_authorized": False}
            self._artifact(con, case_id, "action_plan", plan, "review_required")
            con.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (CaseStatus.REVIEW_REQUIRED, now(), case_id))
            self.audit(con, case_id, "analysis.generated", "system", {"review_required": True})
        return self.get_case(case_id)

    def review(self, case_id: str, req: ReviewRequest) -> dict:
        if req.actor_role != Role.PROFESSIONAL_REVIEWER: raise HTTPException(403, "Professional reviewer role required")
        with self.db.connect() as con:
            self._case(con, case_id)
            data = req.model_dump(mode="json")
            self._artifact(con, case_id, "professional_review", data)
            status = CaseStatus.ACTION_READY if req.decision == "approved" else CaseStatus.REVIEW_REQUIRED
            con.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (status, now(), case_id))
            self.audit(con, case_id, "review.decided", req.actor_id, data)
        return self.get_case(case_id)

    def audit_log(self, case_id: str) -> list[dict]:
        with self.db.connect() as con:
            self._case(con, case_id)
            rows = [dict(r) for r in con.execute("SELECT * FROM audit_events WHERE case_id=? ORDER BY id", (case_id,))]
        for r in rows: r["payload"] = json.loads(r["payload"])
        return rows

    def _message(self, con, case_id: str, role: str, content: str, actor_id: str, citations=None) -> str:
        message_id = f"msg_{uuid4().hex[:12]}"
        con.execute(
            "INSERT INTO messages VALUES(?,?,?,?,?,?,?)",
            (message_id, case_id, role, content, self.db.json(citations or []), actor_id, now()),
        )
        return message_id

    def messages(self, case_id: str, tenant_id: str) -> list[dict]:
        with self.db.connect() as con:
            self._case(con, case_id, tenant_id)
            rows = [dict(r) for r in con.execute("SELECT * FROM messages WHERE case_id=? ORDER BY created_at,id", (case_id,))]
        for row in rows:
            row["citations"] = json.loads(row["citations"])
        return rows

    def chat(self, case_id: str | None, message: str, tenant_id: str, actor_id: str, actor_role: Role) -> dict:
        if not case_id:
            case = self.create_case(CaseCreate(
                purpose=message[:240], tenant_id=tenant_id, actor_id=actor_id, actor_role=actor_role
            ))
            case_id = case["id"]
        else:
            self.get_case(case_id, tenant_id)

        with self.db.connect() as con:
            user_message_id = self._message(con, case_id, "user", message, actor_id)
        self.intake(case_id, actor_id, actor_role, message)
        self._extract_chat_context(case_id, message, actor_id, actor_role, user_message_id)

        with self.db.connect() as con:
            current = {key: self._latest(con, case_id, key) for key in ("locality", "relevant_date", "certificate_status", "dispute_status")}

        questions = [
            ("locality", "Thửa đất nằm tại tỉnh hoặc thành phố nào?"),
            ("relevant_date", "Giao dịch hoặc sự kiện bạn cần xem xét diễn ra vào ngày nào? Bạn có thể trả lời như 14/07/2026."),
            ("certificate_status", "Thửa đất đã có Giấy chứng nhận (sổ đỏ/sổ hồng) chưa?"),
            ("dispute_status", "Hiện thửa đất có tranh chấp, khiếu nại hoặc đang bị xử lý tại cơ quan nào không?"),
        ]
        missing = next(((key, question) for key, question in questions if current[key] is None), None)
        if missing:
            known = self._known_summary(current)
            answer = f"Mình đã ghi nhận{known}.\n\nĐể xác định đúng quy định áp dụng, **{missing[1]}**"
            suggestions = self._suggestions(missing[0])
            return self._chat_reply(case_id, answer, [], suggestions, "intake_in_progress")

        locality, supported = normalize_locality(str(current["locality"]))
        context = ContextRequest(relevant_date=str(current["relevant_date"]), locality=locality)
        self.set_context(case_id, context)
        research = self.research(case_id, ResearchRequest(query="điều kiện chuyển nhượng giấy chứng nhận tranh chấp nghĩa vụ tài chính đăng ký biến động thời hạn"))
        results = self._current_artifact(research, "research_session").get("results", [])
        candidate_results = [item for item in results if item.get("applicability") == "candidate"]
        citations = [{
            "title": item["title"], "location": item["location"],
            "source_id": item["source_id"], "url": item.get("official_url"),
            "version": item.get("snapshot"),
        } for item in candidate_results]
        self.analyze(case_id)

        if current["dispute_status"] is True:
            conclusion = "Hồ sơ có dấu hiệu tranh chấp nên chưa phù hợp để kết luận có thể chuyển nhượng. Cần chuyên gia kiểm tra tình trạng và quyết định giải quyết có hiệu lực trước."
        elif current["certificate_status"] is False:
            conclusion = "Bạn cho biết thửa đất chưa có Giấy chứng nhận. Điều kiện chuyển nhượng thông thường chưa được chứng minh; cần kiểm tra trường hợp ngoại lệ và khả năng cấp Giấy chứng nhận trước."
        else:
            conclusion = "Thông tin ban đầu phù hợp để tiếp tục bước kiểm tra điều kiện và chuẩn bị đăng ký biến động, nhưng chưa đủ để bảo đảm giao dịch sẽ được chấp nhận."

        local_note = (
            "Tại TP.HCM, thủ tục đăng ký biến động do chuyển nhượng được công bố tại thủ tục số 25; thời hạn công bố thông thường không quá 8 ngày làm việc, chưa tính các khoảng thời gian và nghĩa vụ khác theo hồ sơ cụ thể."
            if supported else
            f"Địa phương **{locality}** chưa có source pack riêng. Mình chỉ áp dụng phần luật toàn quốc và không dùng thời hạn, nơi nộp hoặc biểu phí của TP.HCM."
        )
        answer = (
            f"**Nhận định ban đầu**\n\n{conclusion}\n\n"
            "**Các điểm cần kiểm tra**\n\n"
            "- Giấy chứng nhận và đúng chủ thể có quyền chuyển nhượng.\n"
            "- Tình trạng tranh chấp, kê biên hoặc biện pháp khẩn cấp tạm thời.\n"
            "- Thời hạn sử dụng đất và nghĩa vụ tài chính còn ghi nợ.\n"
            "- Điều kiện riêng theo loại đất, người nhận và tài sản gắn liền với đất.\n\n"
            f"**Bước tiếp theo**\n\n{local_note}\n\n"
            "Bạn có thể gửi thêm loại đất, thông tin trên Giấy chứng nhận và mục tiêu giao dịch để mình phân tích sâu hơn."
        )
        return self._chat_reply(case_id, answer, citations, ["Tôi cần chuẩn bị giấy tờ gì?", "Có rủi ro nào cần kiểm tra?", "Giải thích các điều kiện chuyển nhượng"], "review_required")

    def _extract_chat_context(self, case_id: str, message: str, actor_id: str, role: Role, source_id: str):
        lower = message.lower()
        provenance = Provenance.USER_PROVIDED if role == Role.CASE_PARTICIPANT else Provenance.STAFF_ENTERED
        facts: dict[str, object] = {}
        locality, supported = normalize_locality(message)
        if supported or re.search(r"\b(tp\.?\s*hcm|tphcm|hcm|sài gòn|sai gon|hồ chí minh)\b", lower):
            facts["locality"] = "TP. Hồ Chí Minh"
        else:
            locality_match = re.search(r"(?:tại|ở|thuộc)\s+([A-ZÀ-Ỹ][^,.!?]{1,40})", message)
            if locality_match and any(word in lower for word in ("tỉnh", "thành phố", "tp.")):
                facts["locality"] = locality_match.group(1).strip()
        date_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", message)
        iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", message)
        if date_match:
            day, month, year = date_match.groups(); facts["relevant_date"] = f"{year}-{int(month):02d}-{int(day):02d}"
        elif iso_match:
            facts["relevant_date"] = iso_match.group(0)
        elif "hôm nay" in lower:
            facts["relevant_date"] = datetime.now(UTC).date().isoformat()
        if re.search(r"chưa (có )?(sổ|giấy chứng nhận)|không (có )?(sổ|giấy chứng nhận)", lower):
            facts["certificate_status"] = False
        elif re.search(r"(đã |có )(sổ đỏ|sổ hồng|giấy chứng nhận)", lower):
            facts["certificate_status"] = True
        if re.search(r"không (có )?(tranh chấp|khiếu nại|khởi kiện)", lower):
            facts["dispute_status"] = False
        elif re.search(r"tranh chấp|khiếu nại|khởi kiện", lower):
            facts["dispute_status"] = True
        for key, value in facts.items():
            self.add_fact(case_id, FactCreate(key=key, value=value, provenance=provenance, actor_id=actor_id, source_id=source_id, method="chat_context_extraction"))

    @staticmethod
    def _current_artifact(case: dict, type_: str) -> dict:
        items = [a for a in case["artifacts"] if a["type"] == type_ and not a["stale"]]
        return items[-1]["data"] if items else {}

    @staticmethod
    def _known_summary(current: dict) -> str:
        labels = []
        if current.get("locality"): labels.append(f" địa phương là **{current['locality']}**")
        if current.get("relevant_date"): labels.append(f" ngày liên quan **{current['relevant_date']}**")
        return ",".join(labels) if labels else " tình huống ban đầu"

    @staticmethod
    def _suggestions(key: str) -> list[str]:
        return {
            "locality": ["TP.HCM", "Đồng Nai", "Tây Ninh"],
            "relevant_date": ["Hôm nay", "Tôi chưa biết ngày chính xác"],
            "certificate_status": ["Đã có sổ", "Chưa có sổ", "Tôi không chắc"],
            "dispute_status": ["Không có tranh chấp", "Đang có tranh chấp", "Tôi không rõ"],
        }.get(key, [])

    def _chat_reply(self, case_id: str, answer: str, citations: list, suggestions: list, status: str) -> dict:
        with self.db.connect() as con:
            self._message(con, case_id, "assistant", answer, "legal-agent", citations)
        return {"case_id": case_id, "status": status, "answer": answer, "citations": citations, "suggestions": suggestions}
