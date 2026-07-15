from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


# Boundaries reviewed against the official PDFs. Annexes and forms remain in
# full-text.txt for audit, but must not become clauses of the last legal article.
BODY_END_MARKERS = {
    "land-law-consolidated-44-2026-vbhn-vpqh": ["VĂN PHÒNG QUỐC HỘI"],
    "land-law-consolidated-21-2018-vbhn-vpqh": ["VĂN PHÒNG QUỐC HỘI"],
    "decree-101-2024-nd-cp": ["TM. CHÍNH PHỦ"],
    "decree-102-2024-nd-cp": ["TM. CHÍNH PHỦ"],
    "decree-226-2025-nd-cp": ["TM. CHÍNH PHỦ"],
    "decree-49-2026-nd-cp": ["TM. CHÍNH PHỦ"],
    "notarization-consolidated-50-2026-vbhn-vpqh": ["VĂN PHÒNG QUỐC HỘI"],
    "marriage-family-consolidated-121-2025-vbhn-vpqh": ["VĂN PHÒNG QUỐC HỘI"],
    "real-estate-business-consolidated-06-2025-vbhn-vpqh": ["VĂN PHÒNG QUỐC HỘI"],
    "housing-consolidated-79-2026-vbhn-vpqh": ["VĂN PHÒNG QUỐC HỘI"],
    "credit-institutions-consolidated-158-2025-vbhn-vpqh": ["VĂN PHÒNG QUỐC HỘI"],
    "decree-99-2022-nd-cp": ["TM. CHÍNH PHỦ"],
    "decree-104-2025-nd-cp": ["TM. CHÍNH PHỦ"],
    "circular-05-2025-tt-btp": ["KT. BỘ TRƯỞNG"],
    "hcm-decision-44-2026": ["Nơi nhận:"],
}


def main() -> None:
    catalog = json.loads((ROOT / "corpus" / "land" / "manifest-catalog.json").read_text(encoding="utf-8"))
    for entry in catalog["documents"]:
        directory = ROOT / entry["directory"]
        record = json.loads((directory / "acquisition-record.json").read_text(encoding="utf-8"))
        artifacts = [
            {"path": item["path"], "official_url": item["official_url"], "page_count": item["page_count"]}
            for item in record["artifacts"]
        ]
        document = {**entry["document"], "official_url": record["source_page_url"]}
        markers = BODY_END_MARKERS.get(document["id"])
        if markers:
            document["body_end_markers"] = markers
        manifest = {
            "schema_version": 1,
            "document": document,
            "artifacts": artifacts,
            "relationships": entry.get("relationships", []),
        }
        (directory / "source-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {directory / 'source-manifest.json'}")


if __name__ == "__main__":
    main()
