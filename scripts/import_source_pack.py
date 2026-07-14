from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings
from app.database import Database


def validate(pack: dict) -> None:
    doc = pack.get("document", {})
    required = ["id", "title", "number", "authority", "official_url", "content_hash", "effective_from", "legal_status", "jurisdiction", "version"]
    missing = [key for key in required if not doc.get(key)]
    if missing:
        raise ValueError(f"Missing governed document metadata: {', '.join(missing)}")
    if urlparse(doc["official_url"]).scheme != "https":
        raise ValueError("official_url must use HTTPS")
    if doc["legal_status"] not in {"effective", "expired", "not_yet_effective", "superseded"}:
        raise ValueError("legal_status is not controlled")
    if len(doc["content_hash"]) != 64:
        raise ValueError("content_hash must be a SHA-256 hex digest")
    if not pack.get("provisions"):
        raise ValueError("At least one provision is required")
    for provision in pack["provisions"]:
        if not all(provision.get(k) for k in ("id", "location", "text")):
            raise ValueError("Every provision requires id, location, and text")


parser = argparse.ArgumentParser(description="Import a reviewed legal source pack")
parser.add_argument("path", type=Path)
args = parser.parse_args()
pack = json.loads(args.path.read_text(encoding="utf-8"))
validate(pack)
doc = pack["document"]
db = Database(Settings.load().database_path)
with db.connect() as con:
    con.execute(
        """INSERT OR REPLACE INTO legal_documents
        (id,title,number,authority,official_url,content_hash,issued_date,effective_from,effective_to,legal_status,jurisdiction,locality,version,imported_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
        tuple(doc.get(k) for k in ("id","title","number","authority","official_url","content_hash","issued_date","effective_from","effective_to","legal_status","jurisdiction","locality","version")),
    )
    con.execute("DELETE FROM legal_provisions WHERE document_id=?", (doc["id"],))
    con.executemany(
        "INSERT INTO legal_provisions(id,document_id,location,text,keywords) VALUES(?,?,?,?,?)",
        [(p["id"], doc["id"], p["location"], p["text"], json.dumps(p.get("keywords", []), ensure_ascii=False)) for p in pack["provisions"]],
    )
print(f'Imported {doc["id"]} with {len(pack["provisions"])} provisions')
