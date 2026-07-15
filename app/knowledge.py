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
    def __init__(self, db: Database, allow_demo: bool):
        self.db, self.allow_demo = db, allow_demo
        self._search_index: list[tuple[dict, set[str], str]] | None = None
        self._token_index: dict[str, list[int]] | None = None

    def search(self, query: str, context: dict) -> tuple[list[dict], str | None]:
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
        transfer_condition_intent = "chuyen nhuong" in folded_query and "du an" not in folded_query
        notarization_intent = "cong chung" in folded_query
        registration_intent = any(
            phrase in folded_query for phrase in ("dang ky bien dong", "sang ten", "noi nop ho so")
        )
        mortgage_intent = any(
            phrase in folded_query
            for phrase in ("the chap", "ngan hang", "giai chap", "tai san bao dam")
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
                    COALESCE(p.effective_from,d.effective_from) applicable_from,
                    COALESCE(p.effective_to,d.effective_to) applicable_to,
                    p.effective_from provision_effective_from,
                    p.effective_to provision_effective_to,
                    p.legal_status provision_legal_status,
                    d.* FROM legal_provisions p JOIN legal_documents d ON d.id=p.document_id
                    WHERE d.completeness_status='full_text_verified'
                    AND (p.level='article' OR p.level='provision' OR p.level IS NULL)"""
                ).fetchall()
            self._search_index = []
            self._token_index = {}
            for row in rows:
                item = dict(row)
                haystack = self._fold(item["text"] + " " + item["keywords"] + " " + item["title"])
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
            if item.get("locality") and item["locality"] == context.get("locality"):
                score += 12
            if transfer_condition_intent:
                provision_id = str(item.get("provision_id") or "")
                if provision_id == "land-law-consolidated-44-2026-vbhn-vpqh-art-45":
                    score += 24
                elif provision_id in {
                    "law-45-2013-qh13-art-188",
                    "land-law-consolidated-21-2018-vbhn-vpqh-art-188",
                }:
                    score += 24
            if notarization_intent:
                provision_id = str(item.get("provision_id") or "")
                notarization_boosts = {
                    "land-law-consolidated-44-2026-vbhn-vpqh-art-27": 48,
                    "real-estate-business-consolidated-06-2025-vbhn-vpqh-art-44": 32,
                    "notarization-consolidated-50-2026-vbhn-vpqh-art-42": 38,
                    "notarization-consolidated-50-2026-vbhn-vpqh-art-6": 28,
                }
                score += notarization_boosts.get(provision_id, 0)
            if registration_intent:
                provision_id = str(item.get("provision_id") or "")
                registration_boosts = {
                    "decree-101-2024-nd-cp-art-30": 32,
                    "decree-101-2024-nd-cp-art-37": 32,
                    "hcm-decision-44-2026-art-4": 28,
                }
                score += registration_boosts.get(provision_id, 0)
            if mortgage_intent:
                provision_id = str(item.get("provision_id") or "")
                mortgage_boosts = {
                    "civil-code-91-2015-qh13-art-320": 48,
                    "civil-code-91-2015-qh13-art-321": 56,
                    "civil-code-91-2015-qh13-art-327": 30,
                }
                score += mortgage_boosts.get(provision_id, 0)
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
                "jurisdiction": item["jurisdiction"], "locality": item["locality"],
                # This is verbatim extracted provision text, not an AI summary.
                # Keep `summary` temporarily for API compatibility while all
                # decision prompts explicitly prefer `provision_text`.
                "provision_text": item["text"], "summary": item["text"],
                "authority": item["authority"],
                "official_url": item["official_url"], "content_hash": item["content_hash"],
                "applicability": applicability,
                "evidence_role": "historical_reference" if historical_reference else "applicable_rule",
                "governance_status": "full_text_verified",
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
            diversified, deferred = [], []
            per_document: dict[str, int] = {}
            for hit in ordered:
                count = per_document.get(hit["source_id"], 0)
                if count < 2:
                    diversified.append(hit)
                    per_document[hit["source_id"]] = count + 1
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
                AND effective_from<=? AND (effective_to IS NULL OR effective_to>=?) LIMIT 1""",
                (locality, relevant_date, relevant_date),
            ).fetchone()
        return bool(row)
