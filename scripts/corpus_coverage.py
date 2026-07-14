from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from app.config import Settings
from app.database import Database


ROOT = Path(__file__).resolve().parent.parent


def build_report(database_path: str | Path, registry_path: Path | None = None) -> dict:
    registry_path = registry_path or ROOT / "corpus" / "land" / "package-registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    Database(database_path)
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        documents = {
            row["id"]: dict(row)
            for row in con.execute(
                "SELECT id,title,number,legal_status,completeness_status,expected_article_count,parsed_article_count FROM legal_documents"
            )
        }
    finally:
        con.close()

    packages = []
    for package in registry["packages"]:
        required = package["mandatory_documents"]
        document_rows = []
        verified = 0
        acquired = 0
        for document_id in required:
            document = documents.get(document_id)
            acquired += int(document is not None)
            satisfied = bool(
                document
                and document["completeness_status"] == "full_text_verified"
                and document["legal_status"] in {"effective", "expired", "superseded", "partially_effective"}
            )
            verified += int(satisfied)
            document_rows.append({
                "id": document_id,
                "satisfied": satisfied,
                "completeness_status": document["completeness_status"] if document else "missing",
                "legal_status": document["legal_status"] if document else "unknown",
            })
        source_families = package.get("mandatory_source_families", [])
        packages.append({
            "id": package["id"],
            "name": package["name"],
            "priority": package["priority"],
            "declared_status": package["status"],
            "ready": verified == len(required) and not source_families,
            "acquired_documents": acquired,
            "verified_documents": verified,
            "required_documents": len(required),
            "document_coverage_percent": round(100 * verified / len(required), 1) if required else 0.0,
            "pending_source_families": source_families,
            "documents": document_rows,
        })
    return {
        "domain": registry["domain"],
        "registry_version": registry["registry_version"],
        "packages_ready": sum(1 for item in packages if item["ready"]),
        "packages_total": len(packages),
        "packages": packages,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Report governed land-law corpus coverage by business package")
    parser.add_argument("--database", type=Path, default=Path(Settings.load().database_path))
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.database, args.registry)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print(f"Land-law packages ready: {report['packages_ready']}/{report['packages_total']}")
    for package in report["packages"]:
        print(
            f"[{package['priority']}] {package['name']}: "
            f"{package['acquired_documents']}/{package['required_documents']} acquired, "
            f"{package['verified_documents']}/{package['required_documents']} verified; "
            f"{len(package['pending_source_families'])} source families pending; ready={package['ready']}"
        )


if __name__ == "__main__":
    main()
