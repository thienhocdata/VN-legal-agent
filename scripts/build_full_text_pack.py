from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

# Some digitally signed local PDFs OCR the dot after an article number as "ẳ".
# Accept that known glyph substitution while keeping the heading anchored to a line.
ARTICLE_RE = re.compile(r"(?m)^[ \t]*Điều\s+(\d+)[.ẳ]\s*([^\n]*)")
CLAUSE_RE = re.compile(r"(?m)^[ \t]*(\d+)\.\s+(?=\S)")
POINT_RE = re.compile(r"(?m)^[ \t]*([a-zđ])\)\s+(?=\S)", re.IGNORECASE)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_page_text(value: str, *, collapse_horizontal_whitespace: bool = False) -> str:
    value = value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    if collapse_horizontal_whitespace:
        value = "\n".join(re.sub(r"[ \t]{2,}", " ", line) for line in value.splitlines())
    return "\n".join(line.rstrip() for line in value.splitlines()).strip()


def select_article_matches(
    matches: list[re.Match[str]],
    expected_count: int,
    policy: str,
    expected_numbers: list[int] | None = None,
) -> list[re.Match[str]]:
    numbers = [int(match.group(1)) for match in matches]
    expected = expected_numbers or list(range(1, expected_count + 1))
    if len(expected) != expected_count or len(set(expected)) != len(expected):
        raise ValueError("expected_article_numbers must contain expected_article_count unique values")
    if numbers == expected:
        return matches
    if policy not in {"first_complete_sequence", "last_complete_sequence"}:
        raise ValueError(f"Expected {expected_count} unique articles, found {len(set(numbers))}/{len(numbers)}")
    candidates = []
    for start, number in enumerate(numbers):
        if number != expected[0]:
            continue
        candidate = [matches[start]]
        wanted_index = 1
        for index in range(start + 1, len(matches)):
            if wanted_index < len(expected) and numbers[index] == expected[wanted_index]:
                candidate.append(matches[index])
                wanted_index += 1
                if wanted_index == len(expected):
                    candidates.append(candidate)
                    break
    if not candidates:
        raise ValueError(
            f"No complete expected top-level article sequence ({expected_count} articles); "
            f"found {len(set(numbers))}/{len(numbers)} unique/total headings"
        )
    shortest_span = min(item[-1].start() - item[0].start() for item in candidates)
    shortest = [item for item in candidates if item[-1].start() - item[0].start() == shortest_span]
    return shortest[0] if policy == "first_complete_sequence" else shortest[-1]


def source_position(page_spans: list[dict[str, Any]], offset: int) -> dict[str, Any]:
    for page in page_spans:
        if page["start"] <= offset < page["end"]:
            return page
    return page_spans[-1]


def nested_provisions(
    *,
    document_id: str,
    article_number: int,
    article_text: str,
    article_start: int,
    page_spans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    provisions: list[dict[str, Any]] = []
    clause_matches = list(CLAUSE_RE.finditer(article_text))
    clause_occurrences: Counter[str] = Counter()
    for clause_index, match in enumerate(clause_matches):
        clause_number = match.group(1)
        clause_occurrences[clause_number] += 1
        clause_occurrence = clause_occurrences[clause_number]
        # A top-level clause number is unique inside an article. Repeated
        # matches come from footnotes, amendment notes or embedded forms; the
        # complete article text still preserves them for audit.
        if clause_occurrence > 1:
            continue
        end = clause_matches[clause_index + 1].start() if clause_index + 1 < len(clause_matches) else len(article_text)
        clause_text = article_text[match.start():end].strip()
        global_start = article_start + match.start()
        global_end = article_start + max(match.start(), end - 1)
        start_page = source_position(page_spans, global_start)
        end_page = source_position(page_spans, global_end)
        clause_id = f"{document_id}-art-{article_number}-cl-{clause_number}"
        location = f"Điều {article_number} khoản {clause_number}"
        provisions.append({
            "id": clause_id,
            "parent_id": f"{document_id}-art-{article_number}",
            "level": "clause",
            "ordinal": int(clause_number),
            "number": clause_number,
            "location": location,
            "text": clause_text,
            "source_artifact_id": start_page["artifact_id"],
            "source_page_start": start_page["page_number"],
            "source_page_end": end_page["page_number"],
            "keywords": [],
        })
        point_matches = list(POINT_RE.finditer(clause_text))
        point_occurrences: Counter[str] = Counter()
        for point_index, point_match in enumerate(point_matches):
            point_number = point_match.group(1).lower()
            point_occurrences[point_number] += 1
            point_occurrence = point_occurrences[point_number]
            # Point labels are likewise unique within one clause.
            if point_occurrence > 1:
                continue
            point_end = point_matches[point_index + 1].start() if point_index + 1 < len(point_matches) else len(clause_text)
            point_text = clause_text[point_match.start():point_end].strip()
            point_global_start = global_start + point_match.start()
            point_global_end = global_start + max(point_match.start(), point_end - 1)
            point_start_page = source_position(page_spans, point_global_start)
            point_end_page = source_position(page_spans, point_global_end)
            point_id = f"{clause_id}-pt-{point_number}"
            point_location = f"Điều {article_number} khoản {clause_number} điểm {point_number}"
            provisions.append({
                "id": point_id,
                "parent_id": clause_id,
                "level": "point",
                "ordinal": point_index + 1,
                "number": point_number,
                "location": point_location,
                "text": point_text,
                "source_artifact_id": point_start_page["artifact_id"],
                "source_page_start": point_start_page["page_number"],
                "source_page_end": point_end_page["page_number"],
                "keywords": [],
            })
    return provisions


def build(manifest_path: Path) -> tuple[Path, dict[str, int]]:
    from pypdf import PdfReader

    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    document = manifest["document"]
    document_id = document["id"]
    extraction_mode = document.get("pdf_text_extraction_mode", "plain")
    if extraction_mode not in {"plain", "layout"}:
        raise ValueError("pdf_text_extraction_mode must be plain or layout")
    full_text_parts: list[str] = []
    page_spans: list[dict[str, Any]] = []
    artifacts = []
    current_offset = 0

    for part_number, artifact in enumerate(manifest["artifacts"], 1):
        path = (base / artifact["path"]).resolve()
        reader = PdfReader(path)
        if len(reader.pages) != artifact["page_count"]:
            raise ValueError(f"{path.name}: expected {artifact['page_count']} pages, found {len(reader.pages)}")
        artifact_id = f"{document_id}-artifact-{part_number}"
        artifacts.append({
            "path": artifact["path"],
            "official_url": artifact["official_url"],
            "sha256": file_hash(path),
            "media_type": "application/pdf",
            "page_count": len(reader.pages),
        })
        for page_number, page in enumerate(reader.pages, 1):
            marker = f"\n\n[[SOURCE {artifact_id} PAGE {page_number}]]\n"
            extracted = (
                page.extract_text(extraction_mode="layout")
                if extraction_mode == "layout"
                else page.extract_text()
            )
            text = normalized_page_text(
                extracted or "",
                collapse_horizontal_whitespace=extraction_mode == "layout",
            )
            block = marker + text
            start = current_offset + len(marker)
            end = current_offset + len(block)
            page_spans.append({
                "artifact_id": artifact_id,
                "page_number": page_number,
                "start": start,
                "end": end,
            })
            full_text_parts.append(block)
            current_offset = end

    full_text = "".join(full_text_parts).strip() + "\n"
    all_article_matches = list(ARTICLE_RE.finditer(full_text))
    expected_count = document["expected_article_count"]
    article_matches = select_article_matches(
        all_article_matches,
        expected_count,
        document.get("article_selection", "strict"),
        document.get("expected_article_numbers"),
    )
    trailing_match = next(
        (match for match in all_article_matches if match.start() > article_matches[-1].start()),
        None,
    )
    # Official Gazette PDFs commonly append signatures, forms and annexes after
    # the final operative article. Keep those pages in full-text.txt, but do not
    # attach their numbered form fields to the final article as legal clauses.
    body_end = trailing_match.start() if trailing_match else len(full_text)
    for marker in document.get("body_end_markers", []):
        marker_offset = full_text.find(marker, article_matches[-1].end())
        if marker_offset >= 0:
            body_end = min(body_end, marker_offset)
    numbers = [int(match.group(1)) for match in article_matches]
    expected_numbers = set(document.get("expected_article_numbers") or range(1, expected_count + 1))
    if set(numbers) != expected_numbers:
        missing = sorted(expected_numbers - set(numbers))
        extra = sorted(set(numbers) - expected_numbers)
        raise ValueError(f"Article sequence mismatch; missing={missing}, extra={extra}")

    effective_overrides = {str(key): value for key, value in document.get("provision_effective_dates", {}).items()}
    provisions: list[dict[str, Any]] = []
    for index, match in enumerate(article_matches):
        article_number = int(match.group(1))
        end = article_matches[index + 1].start() if index + 1 < len(article_matches) else body_end
        article_text = full_text[match.start():end].strip()
        start_page = source_position(page_spans, match.start())
        end_page = source_position(page_spans, max(match.start(), end - 1))
        article_id = f"{document_id}-art-{article_number}"
        provisions.append({
            "id": article_id,
            "level": "article",
            "ordinal": article_number,
            "number": str(article_number),
            "heading": match.group(2).strip(),
            "location": f"Điều {article_number}",
            "text": article_text,
            "source_artifact_id": start_page["artifact_id"],
            "source_page_start": start_page["page_number"],
            "source_page_end": end_page["page_number"],
            "effective_from": effective_overrides.get(str(article_number), document["effective_from"]),
            "legal_status": "effective",
            "keywords": [],
        })
        provisions.extend(nested_provisions(
            document_id=document_id,
            article_number=article_number,
            article_text=article_text,
            article_start=match.start(),
            page_spans=page_spans,
        ))

    full_text_path = base / "full-text.txt"
    full_text_path.write_text(full_text, encoding="utf-8")
    combined_artifact_hash = hashlib.sha256(
        "".join(artifact["sha256"] for artifact in artifacts).encode("ascii")
    ).hexdigest()
    source_pack = {
        "schema_version": 2,
        "document": {
            **document,
            "content_hash": combined_artifact_hash,
            "source_format": "pdf",
            "full_text_file": full_text_path.name,
            "full_text_hash": file_hash(full_text_path),
            "source_artifacts": artifacts,
        },
        "provisions": provisions,
        "relationships": manifest.get("relationships", []),
    }
    pack_path = base / "source-pack.json"
    pack_path.write_text(json.dumps(source_pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {
        "pages": len(page_spans),
        "characters": len(full_text),
        "articles": sum(1 for item in provisions if item["level"] == "article"),
        "clauses": sum(1 for item in provisions if item["level"] == "clause"),
        "points": sum(1 for item in provisions if item["level"] == "point"),
    }
    return pack_path, counts


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Build a full-text governed source pack from official PDF parts")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    pack_path, counts = build(args.manifest)
    print(f"Built {pack_path}")
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
