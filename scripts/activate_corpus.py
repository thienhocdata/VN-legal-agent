from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import gc
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import Database
from app.knowledge import KnowledgeRepository
from scripts.import_source_pack import import_pack, validate


def discover_verified_packs(corpus_root: Path) -> list[tuple[Path, dict]]:
    """Return only packs that passed governance promotion, after validating bytes."""

    discovered: list[tuple[Path, dict]] = []
    for path in sorted(corpus_root.rglob("source-pack.json")):
        pack = json.loads(path.read_text(encoding="utf-8"))
        if pack.get("document", {}).get("completeness_status") != "full_text_verified":
            continue
        validate(pack, path)
        discovered.append((path, pack))
    if not discovered:
        raise ValueError(f"No full_text_verified source packs found under {corpus_root}")
    return discovered


def _consistent_copy(source: Path, destination: Path) -> None:
    """Create a SQLite-consistent staging copy without mutating the active DB."""

    if not source.exists():
        Database(destination)
        return
    with sqlite3.connect(source) as current, sqlite3.connect(destination) as staging:
        current.backup(staging)
    Database(destination)


def _clear_corpus(database_path: Path) -> None:
    database = Database(database_path)
    with database.connect() as con:
        con.execute("DELETE FROM legal_document_relationships")
        con.execute("DELETE FROM legal_source_artifacts")
        con.execute("DELETE FROM legal_provisions")
        con.execute("DELETE FROM legal_documents")


def _database_counts(database_path: Path) -> tuple[int, int]:
    with sqlite3.connect(database_path) as con:
        documents = con.execute(
            "SELECT count(*) FROM legal_documents WHERE completeness_status='full_text_verified'"
        ).fetchone()[0]
        provisions = con.execute(
            """SELECT count(*) FROM legal_provisions p
            JOIN legal_documents d ON d.id=p.document_id
            WHERE d.completeness_status='full_text_verified'"""
        ).fetchone()[0]
    return int(documents), int(provisions)


def _activate_file(staging_path: Path, active_path: Path) -> None:
    """Swap a fully validated staging DB into place, restoring on any failure."""

    active_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = active_path.with_name(f"{active_path.name}.backup-{uuid4().hex}")
    if not active_path.exists():
        os.replace(staging_path, active_path)
        return
    try:
        os.replace(active_path, backup_path)
    except PermissionError as exc:
        raise RuntimeError(
            "Cannot activate corpus while the runtime database is open. Stop the server and retry."
        ) from exc
    try:
        os.replace(staging_path, active_path)
    except Exception:
        os.replace(backup_path, active_path)
        raise
    else:
        backup_path.unlink(missing_ok=True)


def _remove_staging(path: Path) -> None:
    """Remove SQLite staging files, tolerating short Windows handle delays."""

    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        for attempt in range(10):
            try:
                candidate.unlink(missing_ok=True)
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.05)


def _activate_corpus_unsafe(
    *, corpus_root: Path, active_database: Path, report_path: Path | None = None,
    activate: bool = True, smoke_query: str = "điều kiện chuyển nhượng và sang tên",
    relevant_date: str | None = None,
) -> dict:
    """Validate all packs, build a staging DB, smoke-test it, then atomically activate it."""

    corpus_root = corpus_root.resolve()
    active_database = active_database.resolve()
    packs = discover_verified_packs(corpus_root)
    expected_documents = len(packs)
    expected_provisions = sum(len(pack.get("provisions") or []) for _, pack in packs)
    staging_path = active_database.with_name(
        f"{active_database.name}.staging-{uuid4().hex}.db"
    )
    if staging_path.exists():
        staging_path.unlink()

    try:
        _consistent_copy(active_database, staging_path)
        _clear_corpus(staging_path)
        for pack_path, _pack in packs:
            import_pack(pack_path, staging_path)

        imported_documents, imported_provisions = _database_counts(staging_path)
        if imported_documents != expected_documents:
            raise ValueError(
                f"Document count mismatch: expected {expected_documents}, imported {imported_documents}"
            )
        if imported_provisions != expected_provisions:
            raise ValueError(
                f"Provision count mismatch: expected {expected_provisions}, imported {imported_provisions}"
            )
        with sqlite3.connect(staging_path) as con:
            stale_reviews = con.execute(
                """SELECT count(*) FROM legal_documents
                WHERE completeness_status='full_text_verified'
                AND legal_review_status='stale'"""
            ).fetchone()[0]
        if stale_reviews:
            raise ValueError(f"Stale legal reviews detected: {stale_reviews}")

        database = Database(staging_path)
        previous_revision = database.corpus_revision()
        activated_at = datetime.now(UTC).isoformat()
        runtime_date = relevant_date or date.today().isoformat()
        with database.connect() as con:
            con.execute(
                """UPDATE legal_documents
                SET runtime_activation_status='active'
                WHERE completeness_status='full_text_verified'
                AND artifact_integrity_status='verified'"""
            )
            con.execute(
                """UPDATE corpus_runtime_state
                SET revision=?,activated_at=?,activation_status='validating',report_json='{}'
                WHERE singleton=1""",
                (previous_revision + 1, activated_at),
            )

        repository = KnowledgeRepository(database, allow_demo=False)
        hits, notice = repository.search_by_issues(
            smoke_query,
            {
                "locality": "TP. Hồ Chí Minh",
                "relevant_date": runtime_date,
                "event_timeline": [],
            },
        )
        candidates = [
            item for item in hits
            if item.get("applicability") == "candidate"
            and item.get("governance_status") == "full_text_verified"
        ]
        if not candidates:
            raise ValueError(f"Runtime smoke search returned no governed candidate: {notice}")

        report = {
            "report_version": 1,
            "activated_at": activated_at,
            "corpus_root": str(corpus_root),
            "verification_status": "passed",
            "activation_status": "active" if activate else "validated_only",
            "runtime_status": "search_passed",
            "corpus_revision": previous_revision + 1,
            "expected_documents": expected_documents,
            "imported_documents": imported_documents,
            "expected_provisions": expected_provisions,
            "imported_provisions": imported_provisions,
            "failed_packs": [],
            "runtime_search_passed": True,
            "demo_fallback_used": False,
            "governance": {
                "artifact_integrity_status": "verified",
                "extraction_quality_status": "machine_reviewed",
                "legal_review_status": "machine_assisted",
                "lifecycle_status": "machine_reviewed",
                "runtime_activation_status": "active" if activate else "validated_only",
            },
            "smoke_query": smoke_query,
            "smoke_candidate_ids": [item["provision_id"] for item in candidates[:5]],
        }
        with database.connect() as con:
            con.execute(
                """UPDATE corpus_runtime_state
                SET activation_status=?,report_json=? WHERE singleton=1""",
                (report["activation_status"], json.dumps(report, ensure_ascii=False)),
            )

        if activate:
            _activate_file(staging_path, active_database)
        else:
            _remove_staging(staging_path)
        if report_path:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return report
    except Exception:
        raise


def activate_corpus(
    *, corpus_root: Path, active_database: Path, report_path: Path | None = None,
    activate: bool = True, smoke_query: str = "điều kiện chuyển nhượng và sang tên",
    relevant_date: str | None = None,
) -> dict:
    """Public activation boundary that also removes failed Windows staging files."""

    active_database = active_database.resolve()
    existing_staging = set(
        active_database.parent.glob(f"{active_database.name}.staging-*.db")
    )
    failure_type: type[Exception] | None = None
    failure_args: tuple = ()
    try:
        return _activate_corpus_unsafe(
            corpus_root=corpus_root,
            active_database=active_database,
            report_path=report_path,
            activate=activate,
            smoke_query=smoke_query,
            relevant_date=relevant_date,
        )
    except Exception as exc:
        # Do not retain the original traceback: on Windows it can keep a
        # SQLite statement handle alive until after the except block.
        failure_type = type(exc)
        failure_args = exc.args

    gc.collect()
    new_staging = set(
        active_database.parent.glob(f"{active_database.name}.staging-*.db")
    ) - existing_staging
    for staging_path in new_staging:
        _remove_staging(staging_path)
    assert failure_type is not None
    raise failure_type(*failure_args)


def main() -> None:
    from app.config import Settings

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    settings = Settings.load()
    parser = argparse.ArgumentParser(
        description="Atomically validate and activate the governed legal corpus"
    )
    parser.add_argument("--corpus", type=Path, default=ROOT / "corpus" / "land")
    parser.add_argument("--database", type=Path, default=Path(settings.database_path))
    parser.add_argument(
        "--report", type=Path, default=ROOT / "data" / "corpus-activation-report.json"
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--relevant-date")
    args = parser.parse_args()
    report = activate_corpus(
        corpus_root=args.corpus,
        active_database=args.database,
        report_path=args.report,
        activate=not args.validate_only,
        relevant_date=args.relevant_date,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
