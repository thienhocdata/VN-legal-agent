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

    def search(self, query: str, context: dict) -> tuple[list[dict], str | None]:
        terms = {term for term in self._tokens(query) if len(term) > 2}
        with self.db.connect() as con:
            rows = con.execute(
                """SELECT p.id provision_id,p.location,p.text,p.keywords,
                COALESCE(p.effective_from,d.effective_from) applicable_from,
                COALESCE(p.effective_to,d.effective_to) applicable_to,
                p.effective_from provision_effective_from,
                p.effective_to provision_effective_to,
                p.legal_status provision_legal_status,
                d.* FROM legal_provisions p JOIN legal_documents d ON d.id=p.document_id
                WHERE d.completeness_status='full_text_verified'"""
            ).fetchall()
        hits = []
        relevant_date = context.get("relevant_date")
        for row in rows:
            item = dict(row)
            haystack = self._fold(item["text"] + " " + item["keywords"] + " " + item["title"])
            haystack_tokens = set(self._tokens(haystack))
            score = sum(
                2 if term in haystack else 1
                for term in terms
                if term in haystack or self._near_token(term, haystack_tokens)
            )
            if not score:
                continue
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
            if temporal and locality and status_ok:
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
                "summary": item["text"], "authority": item["authority"],
                "official_url": item["official_url"], "content_hash": item["content_hash"],
                "applicability": applicability,
                "governance_status": "full_text_verified",
                "snapshot": f'{item["id"]}:{item["version"]}:{item["content_hash"][:12]}',
                "score": score,
            })
        if hits:
            return sorted(hits, key=lambda x: x["score"], reverse=True), None
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
