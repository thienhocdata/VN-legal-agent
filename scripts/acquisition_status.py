from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    sources = []
    for path in sorted((ROOT / "corpus" / "land").rglob("acquisition-record.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        artifacts = record.get("artifacts") or ([record["artifact"]] if record.get("artifact") else [])
        sources.append({
            "document_id": record["document_id"],
            "status": record.get("verification_status", record.get("ingestion_status", "legacy_record")),
            "artifacts": len(artifacts),
            "pages": sum(item.get("page_count", 0) for item in artifacts),
            "bytes": sum(item.get("bytes", item.get("byte_size", 0)) for item in artifacts),
            "record": path.relative_to(ROOT).as_posix(),
        })
    blockers = []
    for path in sorted((ROOT / "corpus" / "land").rglob("source-blocker.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        blockers.append({**item, "record": path.relative_to(ROOT).as_posix()})
    report = {
        "report_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "totals": {
            "sources_with_artifacts": len(sources),
            "artifacts": sum(item["artifacts"] for item in sources),
            "pages": sum(item["pages"] for item in sources),
            "bytes": sum(item["bytes"] for item in sources),
            "blockers": len(blockers),
        },
        "sources": sources,
        "blockers": blockers,
    }
    output = ROOT / "corpus" / "land" / "acquisition-status.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
