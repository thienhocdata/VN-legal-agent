from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.import_source_pack import validate


def build_report(pack_path: Path) -> dict:
    pack_path = pack_path.resolve()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    document = pack["document"]
    provisions = pack.get("provisions") or []
    errors: list[str] = []
    try:
        validate(pack, pack_path)
    except ValueError as exc:
        errors.append(str(exc))

    ids = [item.get("id") for item in provisions]
    duplicate_ids = sorted(item for item, count in Counter(ids).items() if item and count > 1)
    articles = [item for item in provisions if item.get("level") == "article"]
    article_numbers = sorted(
        int(item["number"])
        for item in articles
        if str(item.get("number", "")).isdigit()
    )
    expected_count = document.get("expected_article_count")
    expected_sequence = document.get("expected_article_numbers") or (
        list(range(1, expected_count + 1)) if expected_count else []
    )
    empty_provisions = [item.get("id") for item in provisions if not str(item.get("text") or "").strip()]
    candidate_duplicates = [
        item["id"] for item in provisions
        if "ứng viên xuất hiện" in str(item.get("location") or "")
    ]
    checks = {
        "pack_validation_passed": not errors,
        "provision_ids_unique": not duplicate_ids,
        "all_provisions_nonempty": not empty_provisions,
        "article_sequence_complete": article_numbers == expected_sequence,
    }
    structural_passed = all(checks.values())
    status = document.get("completeness_status", "partial")
    return {
        "report_version": 1,
        "checked_at": datetime.now(UTC).isoformat(),
        "document_id": document.get("id"),
        "document_number": document.get("number"),
        "completeness_status": status,
        "checks": checks,
        "errors": errors,
        "metrics": {
            "expected_articles": expected_count,
            "parsed_articles": len(articles),
            "total_provisions": len(provisions),
            "clauses": sum(1 for item in provisions if item.get("level") == "clause"),
            "points": sum(1 for item in provisions if item.get("level") == "point"),
            "candidate_duplicate_nested_locations": len(candidate_duplicates),
        },
        "findings": {
            "duplicate_ids": duplicate_ids,
            "empty_provisions": empty_provisions,
            "candidate_duplicate_nested_location_ids": candidate_duplicates,
        },
        "structural_checks_passed": structural_passed,
        "activation_eligible": structural_passed and status == "full_text_verified",
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Verify structural integrity of a governed source pack")
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.path)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if not report["structural_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
