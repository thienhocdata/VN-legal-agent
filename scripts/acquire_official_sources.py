from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "corpus" / "land" / "acquisition-catalog.json"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def download_pdf(url: str, timeout: int = 120) -> bytes:
    request = Request(url, headers={"User-Agent": "MinhLongLegalAgentCorpus/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        # Some legacy Government CDN certificates validate in the Windows trust store
        # but not in the bundled Python CA bundle. curl still verifies TLS; never use -k.
        result = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--location", url],
            capture_output=True,
            timeout=timeout,
            check=True,
        )
        payload = result.stdout
    if not payload.startswith(b"%PDF-"):
        raise ValueError(f"Official URL did not return a PDF: {url}")
    return payload


def acquire_source(source: dict, *, force: bool = False) -> dict:
    from pypdf import PdfReader

    source_dir = ROOT / source["directory"]
    artifact_dir = source_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    record_path = source_dir / "acquisition-record.json"
    previous = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else {}
    records = []
    for artifact in source["artifacts"]:
        destination = artifact_dir / artifact["filename"]
        if destination.exists() and not force:
            payload = destination.read_bytes()
            if not payload.startswith(b"%PDF-"):
                raise ValueError(f"Existing artifact is not a PDF: {destination}")
        else:
            payload = download_pdf(artifact["official_url"])
            destination.write_bytes(payload)
        page_count = len(PdfReader(destination).pages)
        records.append({
            "path": destination.relative_to(source_dir).as_posix(),
            "official_url": artifact["official_url"],
            "sha256": sha256(payload),
            "bytes": len(payload),
            "page_count": page_count,
        })

    record = {
        "record_version": 1,
        "document_id": source["id"],
        "source_page_url": source["source_page_url"],
        "source_authority": source["source_authority"],
        "acquired_at": datetime.now(UTC).isoformat(),
        "verification_status": previous.get("verification_status", "artifact_downloaded_unverified"),
        "artifacts": records,
    }
    for key in ("visual_verified_at", "visual_verified_by"):
        if previous.get(key):
            record[key] = previous[key]
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return record


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Download governed legal PDFs from approved official URLs")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--id", action="append", dest="ids", help="Acquire only a document id; repeatable")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    selected = [item for item in catalog["sources"] if not args.ids or item["id"] in set(args.ids)]
    unknown = set(args.ids or []) - {item["id"] for item in catalog["sources"]}
    if unknown:
        raise SystemExit(f"Unknown source ids: {', '.join(sorted(unknown))}")
    failures = []
    for source in selected:
        try:
            record = acquire_source(source, force=args.force)
            pages = sum(item["page_count"] for item in record["artifacts"])
            print(f"OK {source['id']}: {len(record['artifacts'])} artifact(s), {pages} page(s)")
        except Exception as exc:  # keep the batch auditable instead of stopping at the first portal error
            failures.append((source["id"], str(exc)))
            print(f"ERROR {source['id']}: {exc}")
    if failures:
        raise SystemExit(f"Acquisition failed for {len(failures)} source(s)")


if __name__ == "__main__":
    main()
