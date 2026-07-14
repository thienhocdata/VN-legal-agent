from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


LEGAL_STATUSES = {"effective", "expired", "not_yet_effective", "superseded", "partially_effective"}
COMPLETENESS_STATUSES = {"summary_only", "excerpt", "partial", "full_text_unverified", "full_text_verified"}
RELATION_TYPES = {
    "amends", "repeals", "replaces", "replaced_by", "implements", "guides",
    "consolidates", "corrects", "references",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolved(base: Path, relative: str) -> Path:
    path = (base / relative).resolve()
    if base.resolve() not in path.parents and path != base.resolve():
        raise ValueError(f"Source-pack path escapes its directory: {relative}")
    return path


def validate(pack: dict, pack_path: Path | None = None) -> None:
    doc = pack.get("document", {})
    required = ["id", "title", "number", "authority", "official_url", "content_hash", "effective_from", "legal_status", "jurisdiction", "version"]
    missing = [key for key in required if not doc.get(key)]
    if missing:
        raise ValueError(f"Missing governed document metadata: {', '.join(missing)}")
    if urlparse(doc["official_url"]).scheme != "https":
        raise ValueError("official_url must use HTTPS")
    if doc["legal_status"] not in LEGAL_STATUSES:
        raise ValueError("legal_status is not controlled")
    if len(doc["content_hash"]) != 64:
        raise ValueError("content_hash must be a SHA-256 hex digest")
    provisions = pack.get("provisions") or []
    if not provisions:
        raise ValueError("At least one provision is required")
    for provision in provisions:
        if not all(provision.get(k) for k in ("id", "location", "text")):
            raise ValueError("Every provision requires id, location, and text")

    completeness = doc.get("completeness_status", "partial")
    if completeness not in COMPLETENESS_STATUSES:
        raise ValueError("completeness_status is not controlled")
    if completeness not in {"full_text_unverified", "full_text_verified"}:
        return
    if pack_path is None:
        raise ValueError("full_text_verified validation requires the source-pack path")
    base = pack_path.resolve().parent
    full_text_file = doc.get("full_text_file")
    artifacts = doc.get("source_artifacts") or []
    expected_articles = doc.get("expected_article_count")
    if not full_text_file or not artifacts or not expected_articles:
        raise ValueError("full_text_verified requires full_text_file, source_artifacts, and expected_article_count")
    full_text_path = _resolved(base, full_text_file)
    if not full_text_path.is_file():
        raise ValueError(f"Missing extracted full text: {full_text_file}")
    if sha256(full_text_path) != doc.get("full_text_hash"):
        raise ValueError("Extracted full-text hash mismatch")
    article_count = sum(1 for item in provisions if item.get("level") == "article")
    if article_count != expected_articles:
        raise ValueError(f"Expected {expected_articles} articles but parsed {article_count}")
    for index, artifact in enumerate(artifacts, 1):
        for key in ("path", "official_url", "sha256", "media_type", "page_count"):
            if not artifact.get(key):
                raise ValueError(f"Artifact {index} is missing {key}")
        if urlparse(artifact["official_url"]).scheme != "https":
            raise ValueError(f"Artifact {index} official_url must use HTTPS")
        artifact_path = _resolved(base, artifact["path"])
        if not artifact_path.is_file() or sha256(artifact_path) != artifact["sha256"]:
            raise ValueError(f"Artifact {index} is missing or has a hash mismatch")
    if completeness == "full_text_verified" and not (doc.get("verified_at") and doc.get("verified_by")):
        raise ValueError("full_text_verified requires verified_at and verified_by")


def import_pack(pack_path: Path, database_path: str | Path) -> tuple[str, int]:
    from app.database import Database

    pack_path = pack_path.resolve()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    validate(pack, pack_path)
    doc = pack["document"]
    base = pack_path.parent
    full_text = None
    if doc.get("full_text_file"):
        full_text = _resolved(base, doc["full_text_file"]).read_text(encoding="utf-8")
    provisions = pack["provisions"]
    db = Database(database_path)
    with db.connect() as con:
        con.execute(
            """INSERT INTO legal_documents
            (id,title,number,authority,official_url,content_hash,issued_date,effective_from,effective_to,
             legal_status,jurisdiction,locality,version,imported_at,document_type,source_format,full_text,
             full_text_hash,completeness_status,expected_article_count,parsed_article_count,
             extraction_method,verified_at,verified_by)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              title=excluded.title, number=excluded.number, authority=excluded.authority,
              official_url=excluded.official_url, content_hash=excluded.content_hash,
              issued_date=excluded.issued_date, effective_from=excluded.effective_from,
              effective_to=excluded.effective_to, legal_status=excluded.legal_status,
              jurisdiction=excluded.jurisdiction, locality=excluded.locality, version=excluded.version,
              imported_at=excluded.imported_at, document_type=excluded.document_type,
              source_format=excluded.source_format, full_text=excluded.full_text,
              full_text_hash=excluded.full_text_hash,
              completeness_status=excluded.completeness_status,
              expected_article_count=excluded.expected_article_count,
              parsed_article_count=excluded.parsed_article_count,
              extraction_method=excluded.extraction_method, verified_at=excluded.verified_at,
              verified_by=excluded.verified_by""",
            (
                doc["id"], doc["title"], doc["number"], doc["authority"], doc["official_url"],
                doc["content_hash"], doc.get("issued_date"), doc["effective_from"], doc.get("effective_to"),
                doc["legal_status"], doc["jurisdiction"], doc.get("locality"), doc["version"],
                doc.get("document_type", "unknown"), doc.get("source_format"), full_text,
                doc.get("full_text_hash"), doc.get("completeness_status", "partial"),
                doc.get("expected_article_count"), sum(1 for p in provisions if p.get("level") == "article"),
                doc.get("extraction_method"), doc.get("verified_at"), doc.get("verified_by"),
            ),
        )
        con.execute("DELETE FROM legal_provisions WHERE document_id=?", (doc["id"],))
        con.executemany(
            """INSERT INTO legal_provisions
            (id,document_id,location,text,keywords,parent_id,level,ordinal,number,heading,
             source_page_start,source_page_end,source_artifact_id,effective_from,effective_to,legal_status,text_hash)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    p["id"], doc["id"], p["location"], p["text"],
                    json.dumps(p.get("keywords", []), ensure_ascii=False), p.get("parent_id"),
                    p.get("level", "provision"), p.get("ordinal"), p.get("number"), p.get("heading"),
                    p.get("source_page_start"), p.get("source_page_end"),
                    p.get("source_artifact_id"),
                    p.get("effective_from"), p.get("effective_to"), p.get("legal_status", "effective"),
                    hashlib.sha256(p["text"].encode("utf-8")).hexdigest(),
                )
                for p in provisions
            ],
        )
        con.execute("DELETE FROM legal_source_artifacts WHERE document_id=?", (doc["id"],))
        for index, artifact in enumerate(doc.get("source_artifacts") or [], 1):
            artifact_path = _resolved(base, artifact["path"])
            con.execute(
                """INSERT INTO legal_source_artifacts
                (id,document_id,part_number,official_url,local_path,media_type,sha256,page_count,byte_size,fetched_at,verified_at)
                VALUES(?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
                (
                    f'{doc["id"]}-artifact-{index}', doc["id"], index, artifact["official_url"],
                    str(artifact_path), artifact["media_type"], artifact["sha256"],
                    artifact.get("page_count"), artifact_path.stat().st_size, doc.get("verified_at"),
                ),
            )
        con.execute("DELETE FROM legal_document_relationships WHERE source_document_id=?", (doc["id"],))
        for index, relation in enumerate(pack.get("relationships") or [], 1):
            if relation.get("relation_type") not in RELATION_TYPES:
                raise ValueError(f"Relationship {index} has an uncontrolled relation_type")
            con.execute(
                """INSERT INTO legal_document_relationships
                (id,source_document_id,source_provision_id,target_document_id,target_provision_id,
                 relation_type,effective_from,evidence_location,note)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    relation.get("id", f'{doc["id"]}-relation-{index}'), doc["id"],
                    relation.get("source_provision_id"), relation["target_document_id"],
                    relation.get("target_provision_id"), relation["relation_type"],
                    relation.get("effective_from"), relation.get("evidence_location"), relation.get("note"),
                ),
            )
    return doc["id"], len(provisions)


def main() -> None:
    from app.config import Settings

    parser = argparse.ArgumentParser(description="Import a reviewed legal source pack")
    parser.add_argument("path", type=Path)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    document_id, count = import_pack(args.path, args.database or Settings.load().database_path)
    print(f"Imported {document_id} with {count} provisions")


if __name__ == "__main__":
    main()
