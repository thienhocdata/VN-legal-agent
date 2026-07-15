"""Governed legal-source registry with an explicitly isolated demo fallback."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher

from .database import Database

DEMO_RULES = [
    {
        "source_id": "LDD-2024-DEMO-45",
        "title": "Luật Đất đai 2024 — demo metadata for transfer conditions",
        "location": "Điều 45 (demo reference; verify against official text)",
        "effective_from": "2024-08-01",
        "effective_to": None,
        "jurisdiction": "Vietnam",
        "locality": None,
        "keywords": ["chuyển nhượng", "giấy chứng nhận", "tranh chấp", "kê biên"],
        "summary": "A transfer analysis must verify the certificate, dispute, enforcement, and other statutory conditions.",
        "authority": "demo_official_metadata",
    },
    {
        "source_id": "LOCAL-PROCEDURE-NOT-CONFIGURED",
        "title": "Local procedure coverage",
        "location": "No locality configured",
        "effective_from": "2024-01-01",
        "effective_to": None,
        "jurisdiction": "Vietnam",
        "locality": "__unsupported__",
        "keywords": ["thủ tục", "hồ sơ", "phí", "văn phòng đăng ký"],
        "summary": "Local operational details require a configured and verified locality source pack.",
        "authority": "system_control",
    },
]


class KnowledgeRepository:
    ISSUE_RULES = (
        ("contract_validity", r"vo hieu|hieu luc hop dong|hop dong.*(?:duoc|khong)|giay tay|dat coc", "giao dịch dân sự điều kiện có hiệu lực hợp đồng đặt cọc vô hiệu"),
        ("transfer_conditions", r"chuyen nhuong|mua ban|ban dat|nhan chuyen nhuong", "điều kiện thực hiện quyền chuyển nhượng quyền sử dụng đất"),
        ("registration", r"sang ten|dang ky bien dong|nop ho so|thu tuc", "đăng ký biến động hồ sơ trình tự cơ quan tiếp nhận"),
        ("mortgage", r"the chap|giai chap|ngan hang|bien phap bao dam", "thế chấp quyền sử dụng đất định đoạt tài sản bảo đảm"),
        ("certificate", r"giay chung nhan|so do|so hong|cap doi|cap lai|dinh chinh", "đăng ký đất đai cấp giấy chứng nhận quyền sử dụng đất"),
        ("parcel", r"tach thua|hop thua|loi di|ranh gioi|moc gioi", "tách thửa hợp thửa diện tích tối thiểu lối đi ranh giới"),
        ("dispute", r"tranh chap|khoi kien|khieu nai|hoa giai", "tranh chấp đất đai hòa giải thẩm quyền giải quyết"),
        ("inheritance", r"thua ke|di chuc|di san", "thừa kế quyền sử dụng đất di chúc di sản"),
        ("planning", r"quy hoach|ke hoach su dung dat|lo gioi|chi gioi", "quy hoạch kế hoạch sử dụng đất xây dựng lộ giới"),
        ("land_use", r"chuyen muc dich|muc dich su dung|dat o|dat nong nghiep", "chuyển mục đích sử dụng đất điều kiện nghĩa vụ"),
        ("state_recovery", r"thu hoi|boi thuong|tai dinh cu|kiem dem", "nhà nước thu hồi đất bồi thường hỗ trợ tái định cư"),
        ("finance", r"thue|le phi|tien su dung dat|tien thue dat|bao nhieu tien", "nghĩa vụ tài chính thuế lệ phí tiền sử dụng đất"),
    )

    def __init__(self, db: Database, allow_demo: bool):
        self.db, self.allow_demo = db, allow_demo
        self._search_index: list[tuple[dict, set[str], str]] | None = None
        self._token_index: dict[str, list[int]] | None = None
        self._loaded_revision: int | None = None

    def invalidate(self) -> None:
        """Drop in-memory retrieval state after a corpus activation."""

        self._search_index = None
        self._token_index = None
        self._loaded_revision = None

    def runtime_status(self) -> dict:
        with self.db.connect() as con:
            state = con.execute(
                """SELECT revision,activated_at,activation_status,report_json
                FROM corpus_runtime_state WHERE singleton=1"""
            ).fetchone()
            documents = con.execute(
                """SELECT count(*) FROM legal_documents
                WHERE completeness_status='full_text_verified'
                AND runtime_activation_status='active'
                AND legal_review_status!='stale'"""
            ).fetchone()[0]
            provisions = con.execute(
                """SELECT count(*) FROM legal_provisions p
                JOIN legal_documents d ON d.id=p.document_id
                WHERE d.completeness_status='full_text_verified'
                AND d.runtime_activation_status='active'
                AND d.legal_review_status!='stale'"""
            ).fetchone()[0]
        report = {}
        if state and state["report_json"]:
            try:
                report = json.loads(state["report_json"])
            except json.JSONDecodeError:
                report = {"report_error": "invalid_json"}
        return {
            "activation_status": state["activation_status"] if state else "not_activated",
            "revision": int(state["revision"]) if state else 0,
            "activated_at": state["activated_at"] if state else None,
            "verified_documents": int(documents),
            "verified_provisions": int(provisions),
            "demo_fallback_enabled": self.allow_demo,
            "last_activation": report,
        }

    def _refresh_if_needed(self) -> None:
        revision = self.db.corpus_revision()
        if self._loaded_revision != revision:
            self._search_index = None
            self._token_index = None
            self._loaded_revision = revision

    def search(self, query: str, context: dict) -> tuple[list[dict], str | None]:
        self._refresh_if_needed()
        ordered_terms = [term for term in self._tokens(query) if len(term) > 2]
        terms = set(ordered_terms)
        folded_query = self._fold(query)
        historical_intent = bool(
            re.search(r"\b(2013|2014|2018|2019|2020|2021|2022|2023)\b", folded_query)
            or any(
                phrase in folded_query
                for phrase in ("so sanh", "luat cu", "quy dinh cu", "truoc day", "lich su")
            )
        )
        query_ngrams = {
            " ".join(ordered_terms[index:index + size]): size
            for size in (2, 3)
            for index in range(len(ordered_terms) - size + 1)
        }
        if self._search_index is None:
            with self.db.connect() as con:
                rows = con.execute(
                    """SELECT p.id provision_id,p.location,p.text,p.keywords,p.heading,
                    p.parent_id,p.level,
                    parent.id parent_provision_id,parent.location parent_location,
                    parent.heading parent_heading,parent.level parent_level,
                    grandparent.id grandparent_provision_id,
                    grandparent.location grandparent_location,
                    grandparent.heading grandparent_heading,
                    COALESCE(p.effective_from,d.effective_from) applicable_from,
                    COALESCE(p.effective_to,d.effective_to) applicable_to,
                    p.effective_from provision_effective_from,
                    p.effective_to provision_effective_to,
                    p.legal_status provision_legal_status,
                    d.id,d.title,d.number,d.authority,d.official_url,d.content_hash,
                    d.effective_from,d.effective_to,d.legal_status,d.jurisdiction,d.locality,
                    d.version,d.document_type,d.completeness_status,
                    d.artifact_integrity_status,d.extraction_quality_status,
                    d.legal_review_status,d.lifecycle_status,d.runtime_activation_status,
                    d.review_fingerprint
                    FROM legal_provisions p JOIN legal_documents d ON d.id=p.document_id
                    LEFT JOIN legal_provisions parent ON parent.id=p.parent_id
                    LEFT JOIN legal_provisions grandparent ON grandparent.id=parent.parent_id
                    WHERE d.completeness_status='full_text_verified'
                    AND d.runtime_activation_status='active'
                    AND d.legal_review_status!='stale'
                    AND (p.level IN ('article','clause','point','provision') OR p.level IS NULL)"""
                ).fetchall()
            self._search_index = []
            self._token_index = {}
            for row in rows:
                item = dict(row)
                haystack = self._fold(
                    item["text"] + " " + item["keywords"] + " " + item["title"] + " "
                    + str(item.get("heading") or "") + " "
                    + str(item.get("parent_heading") or "") + " "
                    + str(item.get("grandparent_heading") or "")
                )
                haystack_token_list = self._tokens(haystack)
                haystack_tokens = set(haystack_token_list)
                item_index = len(self._search_index)
                self._search_index.append((item, haystack_tokens, " ".join(haystack_token_list)))
                for token in haystack_tokens:
                    self._token_index.setdefault(token, []).append(item_index)
        ranked_rows = []
        exact_candidate_indices: set[int] = set()
        for term in terms:
            exact_candidate_indices.update(self._token_index.get(term, []))
        for item_index in exact_candidate_indices:
            item, haystack_tokens, normalized_text = self._search_index[item_index]
            exact_terms = terms & haystack_tokens
            phrase_score = sum(
                3 if size == 2 else 5
                for phrase, size in query_ngrams.items()
                if phrase in normalized_text
            )
            heading_tokens = set(self._tokens(str(item.get("heading") or "")))
            score = 2 * len(exact_terms) + phrase_score + 3 * len(terms & heading_tokens)
            score += {"point": 7, "clause": 5, "article": 2}.get(item.get("level"), 0)
            if item.get("locality") and item["locality"] == context.get("locality"):
                score += 12
            if score:
                ranked_rows.append((item, score))

        # Fuzzy comparison is a typo fallback for a query with no exact corpus
        # match. It must not run against every non-matching provision when the
        # exact retrieval path already produced evidence.
        if not ranked_rows:
            for item, haystack_tokens, _normalized_text in self._search_index:
                score = sum(self._near_token(term, haystack_tokens) for term in terms)
                if score:
                    ranked_rows.append((item, score))

        # Generic words can match thousands of clauses. Only the best-scored
        # candidates need expensive temporal/governance enrichment.
        ranked_rows = sorted(ranked_rows, key=lambda row: row[1], reverse=True)[:240]
        hits = []
        relevant_date = context.get("relevant_date")
        for item, score in ranked_rows:
            applicable_from = item["applicable_from"] or item["effective_from"]
            applicable_to = item["applicable_to"] or item["effective_to"]
            temporal = bool(
                relevant_date and applicable_from <= relevant_date
                and (not applicable_to or relevant_date <= applicable_to)
            )
            locality = item["locality"] is None or item["locality"] == context.get("locality")
            document_current = item["legal_status"] in {"effective", "partially_effective"}
            document_historical = bool(
                item["legal_status"] in {"expired", "repealed", "partially_expired"}
                and applicable_to
                and relevant_date
                and relevant_date <= applicable_to
            )
            provision_current = item["provision_legal_status"] in {"effective", "partially_effective"}
            provision_historical = bool(
                item["provision_legal_status"] in {"expired", "repealed", "partially_expired"}
                and item["provision_effective_to"]
                and relevant_date
                and relevant_date <= item["provision_effective_to"]
            )
            status_ok = (document_current or document_historical) and (
                provision_current or provision_historical
            )
            historical_reference = bool(
                historical_intent
                and locality
                and item["legal_status"] in {"expired", "repealed", "partially_expired"}
            )
            if (temporal and locality and status_ok) or historical_reference:
                applicability = "candidate"
            elif not relevant_date and locality and status_ok:
                applicability = "unverified"
            else:
                applicability = "not_applicable"
            hits.append({
                "source_id": item["id"], "provision_id": item["provision_id"],
                "title": item["title"], "location": item["location"],
                "effective_from": applicable_from, "effective_to": applicable_to,
                "legal_status": item["legal_status"], "document_type": item["document_type"],
                "version": item["version"],
                "jurisdiction": item["jurisdiction"], "locality": item["locality"],
                # This is verbatim extracted provision text, not an AI summary.
                # Keep `summary` temporarily for API compatibility while all
                # decision prompts explicitly prefer `provision_text`.
                "provision_text": item["text"], "summary": item["text"],
                "provision_level": item.get("level") or "provision",
                "parent_context": self._parent_context(item),
                "parent_provision_id": item.get("parent_provision_id"),
                "grandparent_provision_id": item.get("grandparent_provision_id"),
                "article_id": self._article_id(item),
                "authority": item["authority"],
                "official_url": item["official_url"], "content_hash": item["content_hash"],
                "applicability": applicability,
                "evidence_role": "historical_reference" if historical_reference else "applicable_rule",
                "governance_status": "full_text_verified",
                "governance": {
                    "artifact_integrity": item.get("artifact_integrity_status"),
                    "extraction_quality": item.get("extraction_quality_status"),
                    "legal_review": item.get("legal_review_status"),
                    "lifecycle": item.get("lifecycle_status"),
                    "runtime_activation": item.get("runtime_activation_status"),
                    "review_fingerprint": item.get("review_fingerprint"),
                },
                "snapshot": f'{item["id"]}:{item["version"]}:{item["content_hash"][:12]}',
                "score": score,
            })
        if hits:
            applicability_rank = {"candidate": 2, "unverified": 1, "not_applicable": 0}
            ordered = sorted(
                hits,
                key=lambda x: (applicability_rank.get(x["applicability"], 0), x["score"]),
                reverse=True,
            )
            if historical_intent:
                current_rules = [
                    item for item in ordered
                    if item["applicability"] == "candidate"
                    and item.get("evidence_role") != "historical_reference"
                ]
                historical_rules = [
                    item for item in ordered
                    if item["applicability"] == "candidate"
                    and item.get("evidence_role") == "historical_reference"
                ]
                historical_rules.sort(
                    key=lambda item: (
                        str(item.get("version") or "").startswith("consolidated"),
                        item.get("score", 0),
                    ),
                    reverse=True,
                )
                balanced = []
                for index in range(max(len(current_rules), len(historical_rules))):
                    if index < len(historical_rules):
                        balanced.append(historical_rules[index])
                    if index < len(current_rules):
                        balanced.append(current_rules[index])
                balanced_ids = {id(item) for item in balanced}
                ordered = balanced + [item for item in ordered if id(item) not in balanced_ids]
            diversified, deferred = [], []
            per_document: dict[str, int] = {}
            for hit in ordered:
                group_key = f'{hit["source_id"]}:{hit.get("article_id") or hit["provision_id"]}'
                count = per_document.get(group_key, 0)
                if count < 2:
                    diversified.append(hit)
                    per_document[group_key] = count + 1
                else:
                    deferred.append(hit)
            return diversified + deferred, None
        if not self.allow_demo:
            return [], (
                "Không có nguồn toàn văn đã kiểm chứng phù hợp. "
                "Chế độ chính thức không cho phép dùng dữ liệu demo hoặc tài liệu chưa kiểm chứng."
            )
        demo_hits = []
        for rule in DEMO_RULES:
            if any(k.lower() in query.lower() for k in rule["keywords"]):
                applicable = rule["locality"] is None or rule["locality"] == context.get("locality")
                demo_hits.append({
                    **rule,
                    "applicability": "candidate" if applicable else "not_applicable",
                    "governance_status": "demo",
                    "snapshot": rule["source_id"] + ":demo-v1",
                })
        return demo_hits, "Chỉ là corpus demo phát triển; phải kiểm chứng lại bằng nguồn chính thức."

    def search_by_issues(self, query: str, context: dict) -> tuple[list[dict], str | None]:
        """Retrieve a small evidence set for every detected legal issue."""

        folded = self._fold(query)
        issues = [
            (name, expansion)
            for name, pattern, expansion in self.ISSUE_RULES
            if re.search(pattern, folded)
        ]
        if not issues:
            issues = [("general", query)]

        combined: list[dict] = []
        notices: list[str] = []
        by_evidence_group: dict[str, dict] = {}
        for issue, expansion in issues[:6]:
            issue_context = dict(context)
            issue_context["relevant_date"] = self._event_date_for_issue(issue, context)
            hits, notice = self.search(f"{query} {expansion}", issue_context)
            if notice:
                notices.append(notice)
            selected = [item for item in hits if item.get("applicability") == "candidate"][:4]
            if not selected:
                selected = hits[:2]
            for item in selected:
                article_or_provision = item.get("article_id") or item.get("provision_id")
                evidence_group = f'{item.get("source_id")}:{article_or_provision}'
                existing = by_evidence_group.get(evidence_group)
                if existing:
                    issues_for_source = existing.setdefault("legal_issues", [])
                    if issue not in issues_for_source:
                        issues_for_source.append(issue)
                    continue
                enriched = dict(item)
                enriched["legal_issues"] = [issue]
                enriched["applicable_event_date"] = issue_context.get("relevant_date")
                by_evidence_group[evidence_group] = enriched
                combined.append(enriched)

        unique_notice = "; ".join(dict.fromkeys(notices)) or None
        self._hydrate_parent_context(combined)
        return combined, unique_notice

    @staticmethod
    def _event_date_for_issue(issue: str, context: dict) -> str | None:
        timeline = context.get("event_timeline") or []
        preferred = {
            "contract_validity": {"deposit_contract", "transfer_contract", "notarization"},
            "transfer_conditions": {"transfer_contract", "notarization"},
            "registration": {"registration"},
            "mortgage": {"mortgage"},
            "inheritance": {"inheritance"},
            "dispute": {"dispute"},
            "state_recovery": {"state_recovery"},
        }.get(issue, set())
        matches = [item.get("date") for item in timeline if item.get("type") in preferred]
        return matches[-1] if matches else context.get("relevant_date")

    @staticmethod
    def _article_id(item: dict) -> str | None:
        if item.get("level") == "article":
            return item.get("provision_id")
        if item.get("parent_level") == "article":
            return item.get("parent_provision_id")
        return item.get("grandparent_provision_id")

    @staticmethod
    def _parent_context(item: dict) -> str:
        return ""

    def _hydrate_parent_context(self, hits: list[dict]) -> None:
        parent_ids = {
            value
            for item in hits
            for value in (
                item.get("grandparent_provision_id"), item.get("parent_provision_id")
            )
            if value
        }
        if not parent_ids:
            return
        placeholders = ",".join("?" for _ in parent_ids)
        with self.db.connect() as con:
            rows = con.execute(
                f"SELECT id,location,text FROM legal_provisions WHERE id IN ({placeholders})",
                tuple(parent_ids),
            ).fetchall()
        parent_rows = {row["id"]: dict(row) for row in rows}
        for item in hits:
            context_rows = []
            for key in ("grandparent_provision_id", "parent_provision_id"):
                parent = parent_rows.get(item.get(key))
                if parent:
                    context_rows.append(f'{parent["location"]}: {parent["text"]}')
            item["parent_context"] = "\n".join(context_rows)

    @staticmethod
    def _fold(value: str) -> str:
        value = value.lower().replace("đ", "d")
        return "".join(
            char for char in unicodedata.normalize("NFD", value)
            if unicodedata.category(char) != "Mn"
        )

    @classmethod
    def _tokens(cls, value: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", cls._fold(value))

    @staticmethod
    def _near_token(term: str, candidates: set[str]) -> bool:
        if len(term) < 4:
            return False
        return any(
            abs(len(term) - len(candidate)) <= 2
            and candidate[:1] == term[:1]
            and SequenceMatcher(None, term, candidate).ratio() >= 0.75
            for candidate in candidates
        )

    def has_locality(self, locality: str, relevant_date: str | None) -> bool:
        if not relevant_date:
            return False
        with self.db.connect() as con:
            row = con.execute(
                """SELECT 1 FROM legal_documents WHERE locality=? AND legal_status='effective'
                AND completeness_status='full_text_verified'
                AND runtime_activation_status='active'
                AND legal_review_status!='stale'
                AND effective_from<=? AND (effective_to IS NULL OR effective_to>=?) LIMIT 1""",
                (locality, relevant_date, relevant_date),
            ).fetchone()
        return bool(row)
