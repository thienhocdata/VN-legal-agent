from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    catalog = json.loads((ROOT / "corpus" / "land" / "manifest-catalog.json").read_text(encoding="utf-8"))
    for entry in catalog["documents"]:
        directory = ROOT / entry["directory"]
        record = json.loads((directory / "acquisition-record.json").read_text(encoding="utf-8"))
        artifacts = [
            {"path": item["path"], "official_url": item["official_url"], "page_count": item["page_count"]}
            for item in record["artifacts"]
        ]
        manifest = {
            "schema_version": 1,
            "document": {**entry["document"], "official_url": record["source_page_url"]},
            "artifacts": artifacts,
            "relationships": entry.get("relationships", []),
        }
        (directory / "source-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {directory / 'source-manifest.json'}")


if __name__ == "__main__":
    main()
