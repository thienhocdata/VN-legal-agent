from __future__ import annotations

import json
import hashlib
import logging
import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from .database import Database
from .knowledge import KnowledgeRepository
from .legal_ai import LegalAI, LegalAIError
from .coverage import normalize_locality
from .models import CaseCreate, CaseStatus, ContextRequest, FactConfirm, FactCreate, Provenance, ResearchRequest, ReviewRequest, Role


def now() -> str:
    return datetime.now(UTC).isoformat()


class LegalCaseService:
    def __init__(self, db: Database, knowledge: KnowledgeRepository | None = None, legal_ai: LegalAI | None = None):
        self.db = db
        self.knowledge = knowledge or KnowledgeRepository(db, False)
        self.legal_ai = legal_ai
        self.logger = logging.getLogger(__name__)

    def ai_status(self) -> dict:
        if not self.legal_ai:
            return {
                "mode": "unavailable",
                "configured": False,
                "provider": None,
                "model": None,
                "configuration_error": None,
            }
        return self.legal_ai.status()

    def corpus_status(self) -> dict:
        return self.knowledge.runtime_status()

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

        self._extract_chat_context(case_id, message, actor_id, actor_role, user_message_id)

        if self.legal_ai and self.legal_ai.available:
            try:
                return self._ai_chat(case_id, message, tenant_id)
            except LegalAIError as exc:
                self.logger.warning("Legal AI generation failed for %s: %s", case_id, exc)
                with self.db.connect() as con:
                    self.audit(con, case_id, "ai.generation_failed", "legal-agent", {"error": str(exc), "code": exc.code})
                if exc.code in {
                    "rate_limit_exceeded", "insufficient_quota", "timeout",
                    "network", "temporary_unavailable", "all_providers_unavailable",
                }:
                    answer = (
                        "Hệ thống đang tạm quá tải nên chưa thể trả lời lúc này. "
                        "Bạn vui lòng thử lại sau ít phút."
                    )
                else:
                    answer = (
                        "Trợ lý đang tạm ngưng để kiểm tra hệ thống. "
                        "Bạn vui lòng thử lại sau hoặc liên hệ người quản trị."
                    )
                return self._chat_reply(case_id, answer, [], [], "ai_unavailable")

        return self._chat_reply(
            case_id,
            "Trợ lý AI hiện chưa được kết nối. Bạn vui lòng thử lại sau khi hệ thống được cấu hình.",
            [],
            [],
            "ai_unavailable",
        )

    def _ai_chat(self, case_id: str, message: str, tenant_id: str) -> dict:
        case = self.get_case(case_id, tenant_id)
        facts: dict[str, object] = {}
        fact_records_by_key: dict[str, dict[str, object]] = {}
        for fact in case["facts"]:
            # The first utterance is stored as case_purpose for workflow/audit
            # compatibility. It is not a legal fact and must not bias later
            # answers (for example, a conversation that started with "alo").
            if fact["key"] != "case_purpose":
                facts[fact["key"]] = fact["value"]
                fact_records_by_key[fact["key"]] = {
                    "key": fact["key"],
                    "value": fact["value"],
                    "provenance": fact["provenance"],
                    "confirmation_status": (
                        "confirmed"
                        if fact["provenance"] in {
                            Provenance.USER_CONFIRMED,
                            Provenance.PROFESSIONAL_CONFIRMED,
                        }
                        else "unconfirmed"
                    ),
                    "source_message_id": fact.get("source_id"),
                }

        context = {
            "locality": facts.get("locality"),
            "relevant_date": facts.get("relevant_date"),
            "event_timeline": facts.get("event_timeline") or [],
        }
        sources, source_notice = self.knowledge.search_by_issues(message, context)
        history = self.messages(case_id, tenant_id)
        result = self.legal_ai.generate(
            history=history,
            facts=facts,
            fact_records=list(fact_records_by_key.values()),
            sources=sources,
            source_notice=source_notice,
            question=message,
        )
        cited_indexes = {
            int(value)
            for value in re.findall(r"\[Nguồn\s+(\d+)\]", result.answer, flags=re.IGNORECASE)
        }
        citations = [
            {
                "title": item["title"],
                "location": item["location"],
                "source_id": item["source_id"],
                "url": item.get("official_url"),
                "version": item.get("snapshot"),
            }
            for index, item in enumerate(sources, 1)
            if item.get("applicability") == "candidate"
            and item.get("governance_status") == "full_text_verified"
            and (not result.decision_audit or index in cited_indexes)
        ]
        with self.db.connect() as con:
            audit_summary: dict[str, object] | None = None
            if result.internal_audit:
                try:
                    payload = json.loads(result.internal_audit)
                    audit_summary = {
                        "sha256": hashlib.sha256(
                            result.internal_audit.encode("utf-8")
                        ).hexdigest(),
                        "issues": [
                            {"issue": item.get("issue"), "status": item.get("status")}
                            for item in payload.get("issues") or []
                            if isinstance(item, dict)
                        ],
                    }
                except (ValueError, TypeError):
                    audit_summary = {"status": "unparseable"}
            self.audit(
                con,
                case_id,
                "ai.response_generated",
                "legal-agent",
                {
                    "provider": result.provider,
                    "model": result.model,
                    "generation_mode": result.generation_mode,
                    "provider_called": result.provider_called,
                    "provider_model": result.provider_model or result.model,
                    "source_ids": [item["source_id"] for item in sources],
                    "decision_audit": result.decision_audit,
                    "internal_audit_summary": audit_summary,
                    "response_status": result.response_status,
                },
            )
        return self._chat_reply(
            case_id, result.answer, citations, result.suggestions, result.response_status
        )

    def _extract_chat_context(self, case_id: str, message: str, actor_id: str, role: Role, source_id: str):
        lower = message.lower()
        folded = self.knowledge._fold(message)
        provenance = Provenance.USER_PROVIDED if role == Role.CASE_PARTICIPANT else Provenance.STAFF_ENTERED
        facts: dict[str, object] = {}
        locality, supported = normalize_locality(message)
        if supported or re.search(r"\b(tp\.?\s*hcm|tphcm|hcm|sài gòn|sai gon|hồ chí minh)\b", lower):
            facts["locality"] = "TP. Hồ Chí Minh"
        else:
            locality_match = re.search(r"(?:tại|ở|thuộc)\s+([A-ZÀ-Ỹ][^,.!?]{1,40})", message)
            if locality_match and any(word in lower for word in ("tỉnh", "thành phố", "tp.")):
                facts["locality"] = locality_match.group(1).strip()
        events = self._extract_legal_events(message, source_id)
        if events:
            with self.db.connect() as con:
                previous_events = self._latest(con, case_id, "event_timeline") or []
            merged = {
                (item["type"], item["date"], item.get("source_message_id")): item
                for item in [*previous_events, *events]
            }
            facts["event_timeline"] = sorted(
                merged.values(), key=lambda item: (item["date"], item["type"])
            )
        if len(events) == 1:
            facts["relevant_date"] = events[0]["date"]
        elif "hôm nay" in lower:
            facts["relevant_date"] = datetime.now(UTC).date().isoformat()
        elif re.search(r"\b(hiện nay|bây giờ|lúc này|ngay bây giờ|đang)\b", lower):
            # Present-tense questions are evaluated at the current date unless
            # the user supplies a different event date later.
            facts["relevant_date"] = datetime.now(UTC).date().isoformat()
        certificate_question = bool(re.search(
            r"\bco\W+(?:so do|so hong|giay chung nhan)\W+(?:khong|ko|k)\b",
            folded,
        ))
        if not certificate_question and re.search(
            r"\b(?:chua|khong|ko|k)\W*(?:co\W*)?(?:so|giay chung nhan)", folded
        ):
            facts["certificate_status"] = False
        elif not certificate_question and re.search(
            r"\b(?:da|co|dang\W+dung\W+ten)\W+(?:so do|so hong|giay chung nhan)", folded
        ):
            facts["certificate_status"] = True
        dispute_negative = bool(re.search(
            r"\b(?:khong|ko|k)\W*(?:co\W*)?(?:tranh chap|khieu nai|khoi kien)", folded
        ))
        dispute_question = not dispute_negative and bool(re.search(
            r"\bco\W+(?:tranh chap|khieu nai|khoi kien)\W+(?:khong|ko|k)\b",
            folded,
        ))
        if dispute_negative:
            facts["dispute_status"] = False
            facts["dispute_report_status"] = "reported_absent"
        elif not dispute_question and re.search(r"tranh chap|khieu nai|khoi kien", folded):
            if re.search(r"da\W+(?:duoc\W+)?(?:giai quyet|rut don)|da\W+co\W+ban an", folded):
                facts["dispute_status"] = False
                facts["dispute_report_status"] = "resolved"
            else:
                facts["dispute_status"] = True
            if re.search(r"ghi nhan\W+chinh thuc", folded):
                facts["dispute_report_status"] = "officially_recorded"
            elif re.search(r"thu ly|quyet dinh\W+thu ly", folded):
                facts["dispute_report_status"] = "accepted"
            elif re.search(r"co quan .*da\W+(?:tiep nhan|nhan)|da\W+duoc\W+tiep nhan", folded):
                facts["dispute_report_status"] = "received"
            elif re.search(r"da\W+(?:nop|gui)\W+(?:don|don kien|don khieu nai)", folded):
                facts["dispute_report_status"] = "submitted"
            elif facts.get("dispute_report_status") != "resolved":
                facts["dispute_report_status"] = "alleged"
        if re.search(r"\b(?:khong|ko|k)\W*(?:bi\W*)?ke bien", folded):
            facts["enforcement_status"] = False
        if re.search(r"con\W+(?:thoi\W+)?han\W+su\W+dung", folded):
            facts["land_term_status"] = True
        mortgage_negative = bool(re.search(
            r"\b(?:khong|ko|k|chua)\W*(?:dang\W+)?the chap", folded
        ))
        mortgage_question = not mortgage_negative and bool(re.search(
            r"\bco\W+(?:dang\W+)?the chap\W+(?:khong|ko|k)\b", folded
        ))
        if mortgage_negative:
            facts["mortgage_status"] = False
        elif not mortgage_question and re.search(
            r"(?:van\W+|hien\W+|van\W+con\W+)?dang\W+the chap|con\W+the chap", folded
        ):
            facts["mortgage_status"] = True
        if re.search(r"ngân hàng (?:vẫn )?chưa (?:có văn bản )?(?:đồng ý|chấp thuận)", lower):
            facts["mortgagee_consent_status"] = False
        elif re.search(r"ngân hàng (?:đã )?(?:có văn bản )?(?:đồng ý|chấp thuận)", lower):
            facts["mortgagee_consent_status"] = True
        if re.search(r"hợp đồng (?:chuyển nhượng )?(?:đã )?được công chứng", lower):
            facts["contract_notarized_status"] = True
        for key, value in facts.items():
            self.add_fact(case_id, FactCreate(key=key, value=value, provenance=provenance, actor_id=actor_id, source_id=source_id, method="chat_context_extraction"))

    @staticmethod
    def _extract_legal_events(message: str, source_message_id: str) -> list[dict[str, str]]:
        """Extract dated legal events without collapsing a case into one date."""

        date_matches: list[tuple[int, int, str]] = []
        for match in re.finditer(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b", message):
            day, month, year = match.groups()
            try:
                parsed = datetime(int(year), int(month), int(day), tzinfo=UTC).date().isoformat()
            except ValueError:
                continue
            date_matches.append((match.start(), match.end(), parsed))
        for match in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", message):
            year, month, day = match.groups()
            try:
                parsed = datetime(int(year), int(month), int(day), tzinfo=UTC).date().isoformat()
            except ValueError:
                continue
            date_matches.append((match.start(), match.end(), parsed))

        event_patterns = (
            ("deposit_contract", r"đặt cọc|hợp đồng cọc|dat coc|hop dong coc"),
            ("mortgage", r"thế chấp|giải chấp|ngân hàng|the chap|giai chap|ngan hang"),
            ("notarization", r"công chứng|chứng thực|cong chung|chung thuc"),
            ("transfer_contract", r"chuyển nhượng|mua bán|hợp đồng bán|chuyen nhuong|mua ban|hop dong ban"),
            ("registration", r"sang tên|đăng ký biến động|sang ten|dang ky bien dong"),
            ("inheritance", r"thừa kế|di chúc|thua ke|di chuc"),
            ("dispute", r"tranh chấp|khởi kiện|khiếu nại|tranh chap|khoi kien|khieu nai"),
            ("state_recovery", r"thu hồi|bồi thường|tái định cư|thu hoi|boi thuong|tai dinh cu"),
        )
        event_mentions = [
            (match.start(), match.end(), event_type)
            for event_type, pattern in event_patterns
            for match in re.finditer(pattern, message.lower())
        ]
        events = []
        for start, end, event_date in sorted(set(date_matches)):
            event_type = "unspecified_legal_event"
            if event_mentions:
                date_center = (start + end) / 2
                segment_start = max(
                    message.rfind(marker, 0, start) for marker in (",", ";", ".", "!", "?")
                ) + 1
                preceding = [
                    item for item in event_mentions
                    if segment_start <= item[0] and item[1] <= start
                ]
                mention = max(preceding, key=lambda item: item[1]) if preceding else min(
                    event_mentions,
                    key=lambda item: abs(((item[0] + item[1]) / 2) - date_center),
                )
                if abs(((mention[0] + mention[1]) / 2) - date_center) <= 120:
                    event_type = mention[2]
            events.append({
                "type": event_type,
                "date": event_date,
                "source_message_id": source_message_id,
                "confirmation_status": "unconfirmed",
            })
        return events

    @staticmethod
    def _current_artifact(case: dict, type_: str) -> dict:
        items = [a for a in case["artifacts"] if a["type"] == type_ and not a["stale"]]
        return items[-1]["data"] if items else {}

    def _chat_reply(self, case_id: str, answer: str, citations: list, suggestions: list, status: str) -> dict:
        with self.db.connect() as con:
            self._message(con, case_id, "assistant", answer, "legal-agent", citations)
        return {"case_id": case_id, "status": status, "answer": answer, "citations": citations, "suggestions": suggestions}
