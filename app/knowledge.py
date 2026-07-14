"""Governed legal-source registry with an explicitly isolated demo fallback."""

from __future__ import annotations

import json
from datetime import date

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
        terms = {term.lower() for term in query.split() if len(term) > 2}
        with self.db.connect() as con:
            rows = con.execute(
                """SELECT p.id provision_id,p.location,p.text,p.keywords,
                d.* FROM legal_provisions p JOIN legal_documents d ON d.id=p.document_id"""
            ).fetchall()
        hits = []
        relevant_date = context.get("relevant_date")
        for row in rows:
            item = dict(row)
            haystack = (item["text"] + " " + item["keywords"] + " " + item["title"]).lower()
            score = sum(1 for t in terms if t in haystack)
            if not score:
                continue
            temporal = bool(relevant_date and item["effective_from"] <= relevant_date and (not item["effective_to"] or relevant_date <= item["effective_to"]))
            locality = item["locality"] is None or item["locality"] == context.get("locality")
            status_ok = item["legal_status"] == "effective"
            hits.append({
                "source_id": item["id"], "provision_id": item["provision_id"],
                "title": item["title"], "location": item["location"],
                "effective_from": item["effective_from"], "effective_to": item["effective_to"],
                "jurisdiction": item["jurisdiction"], "locality": item["locality"],
                "summary": item["text"], "authority": item["authority"],
                "official_url": item["official_url"], "content_hash": item["content_hash"],
                "applicability": "candidate" if temporal and locality and status_ok else "not_applicable",
                "snapshot": f'{item["id"]}:{item["version"]}:{item["content_hash"][:12]}',
                "score": score,
            })
        if hits:
            return sorted(hits, key=lambda x: x["score"], reverse=True), None
        if not self.allow_demo:
            return [], "No governed source matched. Pilot mode forbids demo-source fallback."
        demo_hits = []
        for rule in DEMO_RULES:
            if any(k.lower() in query.lower() for k in rule["keywords"]):
                applicable = rule["locality"] is None or rule["locality"] == context.get("locality")
                demo_hits.append({**rule, "applicability": "candidate" if applicable else "not_applicable", "snapshot": rule["source_id"] + ":demo-v1"})
        return demo_hits, "Development demo corpus only; official-source verification required."

    def has_locality(self, locality: str, relevant_date: str | None) -> bool:
        if not relevant_date:
            return False
        with self.db.connect() as con:
            row = con.execute(
                """SELECT 1 FROM legal_documents WHERE locality=? AND legal_status='effective'
                AND effective_from<=? AND (effective_to IS NULL OR effective_to>=?) LIMIT 1""",
                (locality, relevant_date, relevant_date),
            ).fetchone()
        return bool(row)
