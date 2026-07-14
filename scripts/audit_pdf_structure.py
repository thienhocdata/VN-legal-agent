from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_full_text_pack import ARTICLE_RE, normalized_page_text


def audit(record_path: Path) -> dict:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    text_parts = []
    total_pages = 0
    for artifact in record["artifacts"]:
        reader = PdfReader(record_path.parent / artifact["path"])
        total_pages += len(reader.pages)
        text_parts.extend(normalized_page_text(page.extract_text() or "") for page in reader.pages)
    text = "\n".join(text_parts)
    numbers = [int(match.group(1)) for match in ARTICLE_RE.finditer(text)]
    unique = sorted(set(numbers))
    return {
        "document_id": record["document_id"],
        "pages": total_pages,
        "characters": len(text),
        "characters_per_page": round(len(text) / total_pages) if total_pages else 0,
        "article_heading_matches": len(numbers),
        "unique_article_numbers": len(unique),
        "article_range": [unique[0], unique[-1]] if unique else [],
        "article_sequence_contiguous": bool(unique) and unique == list(range(1, unique[-1] + 1)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit PDF text and top-level article structure before pack building")
    parser.add_argument("--id", action="append", dest="ids")
    args = parser.parse_args()
    reports = []
    for path in sorted((ROOT / "corpus" / "land").rglob("acquisition-record.json")):
        document_id = json.loads(path.read_text(encoding="utf-8"))["document_id"]
        if args.ids and document_id not in set(args.ids):
            continue
        reports.append(audit(path))
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
