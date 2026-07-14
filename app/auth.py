from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from fastapi import Header, HTTPException

from .database import Database
from .models import Role


@dataclass(frozen=True)
class Principal:
    actor_id: str
    tenant_id: str
    role: Role


def hash_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def issue_api_key(db: Database, actor_id: str, tenant_id: str, role: Role) -> str:
    raw = "mla_" + secrets.token_urlsafe(32)
    with db.connect() as con:
        con.execute(
            "INSERT INTO api_keys(id,key_hash,actor_id,tenant_id,role,active,created_at) VALUES(?,?,?,?,?,1,datetime('now'))",
            ("key_" + secrets.token_hex(8), hash_key(raw), actor_id, tenant_id, role),
        )
    return raw


class Authenticator:
    def __init__(self, db: Database, required: bool):
        self.db, self.required = db, required

    def principal(self, x_api_key: str | None = Header(default=None)) -> Principal:
        if not self.required and not x_api_key:
            return Principal("demo-user", "demo", Role.CASE_PARTICIPANT)
        if not x_api_key:
            raise HTTPException(401, "X-API-Key is required")
        with self.db.connect() as con:
            row = con.execute("SELECT actor_id,tenant_id,role FROM api_keys WHERE key_hash=? AND active=1", (hash_key(x_api_key),)).fetchone()
        if not row:
            raise HTTPException(401, "Invalid API key")
        return Principal(row["actor_id"], row["tenant_id"], Role(row["role"]))

