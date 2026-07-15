from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a completed first/middle/last PDF visual review")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--sample-directory", type=Path, default=ROOT / "tmp" / "pdfs" / "qa")
    args = parser.parse_args()
    sample_directory = args.sample_directory
    if not sample_directory.is_absolute():
        sample_directory = ROOT / sample_directory
    sample_directory = sample_directory.resolve()
    checked_at = datetime.now(UTC).isoformat()
    count = 0
    for record_path in sorted((ROOT / "corpus" / "land").rglob("acquisition-record.json")):
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("verification_status") != "artifact_downloaded_unverified":
            continue
        document_id = record["document_id"]
        samples = {
            tag: sample_directory / f"{document_id}-{tag}.png"
            for tag in ("first", "middle", "last")
        }
        if not all(path.exists() for path in samples.values()):
            continue
        report = {
            "report_version": 1,
            "document_id": document_id,
            "checked_at": checked_at,
            "checked_by": args.reviewer,
            "sampling": "first_middle_last_across_artifact_set",
            "samples": {tag: path.relative_to(ROOT).as_posix() for tag, path in samples.items()},
            "checks": {
                "correct_document_identity": True,
                "pages_readable": True,
                "page_order_plausible": True,
                "no_portal_error_page": True,
            },
            "visual_checks_passed": True,
            "note": "Visual acceptance covers artifact identity and readability only; legal status and extracted text remain separately governed.",
        }
        (record_path.parent / "visual-qa.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        record["verification_status"] = "artifact_visual_verified_text_unverified"
        record["visual_verified_at"] = checked_at
        record["visual_verified_by"] = args.reviewer
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1
    print(f"Recorded visual QA for {count} source(s)")


if __name__ == "__main__":
    main()
