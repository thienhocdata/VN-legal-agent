from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verify_source_pack import build_report


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_REVIEW_CHECKS = {
    "source_identity_confirmed",
    "artifact_hashes_match",
    "visual_sampling_passed",
    "article_structure_and_gaps_reviewed",
    "effectivity_checked",
    "amendments_and_interdisciplinary_relations_checked",
    "direct_evidence_ready",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def preflight(directory: Path, applicability_date: str) -> tuple[dict, dict, dict, dict]:
    pack_path = directory / "source-pack.json"
    paths = {
        "pack": pack_path,
        "manifest": directory / "source-manifest.json",
        "acquisition": directory / "acquisition-record.json",
        "visual": directory / "visual-qa.json",
        "integrity": directory / "integrity-report.json",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError(f"Missing activation evidence: {', '.join(missing)}")

    pack = _load(paths["pack"])
    manifest = _load(paths["manifest"])
    acquisition = _load(paths["acquisition"])
    visual = _load(paths["visual"])
    integrity = _load(paths["integrity"])
    document = pack["document"]
    document_id = document["id"]

    if manifest["document"]["id"] != document_id or acquisition["document_id"] != document_id:
        raise ValueError("Document identity differs across governed evidence files")
    if document["official_url"] != acquisition["source_page_url"]:
        raise ValueError("Official source-page URL differs between pack and acquisition record")
    if acquisition.get("verification_status") != "artifact_visual_verified_text_unverified":
        raise ValueError("Official artifact has not passed visual QA")
    if not visual.get("visual_checks_passed") or visual.get("document_id") != document_id:
        raise ValueError("Visual QA report did not pass for this document")
    if not all(visual.get("checks", {}).values()):
        raise ValueError("One or more visual QA checks failed")
    if not integrity.get("structural_checks_passed") or integrity.get("document_id") != document_id:
        raise ValueError("Structural integrity report did not pass for this document")
    if integrity.get("metrics", {}).get("candidate_duplicate_nested_locations"):
        raise ValueError("Duplicate nested provision candidates must be resolved before activation")

    acquired = acquisition.get("artifacts", [])
    packed = document.get("source_artifacts", [])
    if len(acquired) != len(packed) or not acquired:
        raise ValueError("Artifact set differs between acquisition record and source pack")
    for source, artifact in zip(acquired, packed, strict=True):
        if any(source.get(key) != artifact.get(key) for key in ("path", "official_url", "sha256", "page_count")):
            raise ValueError("Artifact metadata differs between acquisition record and source pack")
        artifact_path = directory / artifact["path"]
        if not artifact_path.is_file() or _sha256(artifact_path) != artifact["sha256"]:
            raise ValueError(f"Artifact hash mismatch: {artifact.get('path')}")

    as_of = date.fromisoformat(applicability_date)
    effective_from = date.fromisoformat(document["effective_from"])
    effective_to = date.fromisoformat(document["effective_to"]) if document.get("effective_to") else None
    if effective_from > as_of or (effective_to and effective_to < as_of):
        raise ValueError(f"Document is not applicable on {applicability_date}")
    if document["legal_status"] not in {"effective", "partially_effective", "expired", "superseded"}:
        raise ValueError("Document lifecycle status is not eligible for current or historical retrieval")
    if document["legal_status"] == "partially_effective" and not pack.get("relationships"):
        raise ValueError("Partially effective document requires an amendment relationship graph")
    return pack, manifest, acquisition, integrity


def promote(directory: Path, *, reviewer: str, applicability_date: str) -> dict:
    pack, manifest, acquisition, integrity = preflight(directory, applicability_date)
    document = pack["document"]
    document_id = document["id"]
    reviewed_at = datetime.now(UTC).isoformat()
    review = {
        "review_version": 1,
        "document_id": document_id,
        "reviewed_at": reviewed_at,
        "reviewed_by": reviewer,
        "review_level": "machine_assisted_official_source_review",
        "applicability_date": applicability_date,
        "official_source_page": acquisition["source_page_url"],
        "legal_status_reviewed": document["legal_status"],
        "relationships_reviewed": pack.get("relationships", []),
        "checks": {name: True for name in sorted(REQUIRED_REVIEW_CHECKS)},
        "note": (
            "Activation verifies official-source identity, immutable artifact hashes, visual samples, "
            "complete article structure, applicability metadata and declared amendment relationships. "
            "It is a machine-assisted corpus review, not an opinion on a specific legal matter."
        ),
    }
    for governed_document in (pack["document"], manifest["document"]):
        governed_document["completeness_status"] = "full_text_verified"
        governed_document["verified_at"] = reviewed_at
        governed_document["verified_by"] = reviewer
        governed_document["verification_level"] = review["review_level"]

    catalog_path = ROOT / "corpus" / "land" / "manifest-catalog.json"
    catalog = _load(catalog_path)
    catalog_match = next(
        (item for item in catalog["documents"] if item["document"]["id"] == document_id),
        None,
    )
    if catalog_match is None:
        catalog_match = manifest
        catalog["documents"].append(catalog_match)
    catalog_match["document"].update({
        "completeness_status": "full_text_verified",
        "verified_at": reviewed_at,
        "verified_by": reviewer,
        "verification_level": review["review_level"],
    })

    # All preflight and catalog checks are complete before governed files are
    # mutated, avoiding a half-promoted pack when a catalog entry is new.
    _write(directory / "activation-review.json", review)
    _write(directory / "source-pack.json", pack)
    _write(directory / "source-manifest.json", manifest)
    _write(catalog_path, catalog)

    report = build_report(directory / "source-pack.json")
    if not report["activation_eligible"]:
        raise ValueError(f"Post-promotion verification failed for {document_id}")
    _write(directory / "integrity-report.json", report)
    return review


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Promote reviewed official source packs into the active corpus")
    parser.add_argument("--document-id", action="append", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--applicability-date", required=True)
    parser.add_argument(
        "--attest-reviewed",
        action="store_true",
        help="Confirm that identity, effectivity, relationships and extracted structure were reviewed",
    )
    args = parser.parse_args()
    if not args.attest_reviewed:
        raise SystemExit("Refusing promotion without --attest-reviewed")

    directories = {}
    for manifest_path in (ROOT / "corpus" / "land").rglob("source-manifest.json"):
        manifest = _load(manifest_path)
        directories[manifest["document"]["id"]] = manifest_path.parent
    unknown = set(args.document_id) - set(directories)
    if unknown:
        raise SystemExit(f"Unknown source pack(s): {', '.join(sorted(unknown))}")
    for document_id in args.document_id:
        review = promote(
            directories[document_id],
            reviewer=args.reviewer,
            applicability_date=args.applicability_date,
        )
        print(f"PROMOTED {document_id} at {review['reviewed_at']}")


if __name__ == "__main__":
    main()
