"""Normalize governed full text to LF and refresh its declared byte hash."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def normalize_pack(pack_path: Path) -> tuple[str, bool]:
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    document = pack["document"]
    full_text_name = document.get("full_text_file")
    if not full_text_name:
        return document["id"], False
    full_text_path = pack_path.parent / full_text_name
    original = full_text_path.read_bytes()
    normalized = original.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    digest = hashlib.sha256(normalized).hexdigest()
    changed = normalized != original or document.get("full_text_hash") != digest
    if changed:
        full_text_path.write_bytes(normalized)
        document["full_text_hash"] = digest
        with pack_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(pack, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    return document["id"], changed


def main() -> None:
    packs = sorted((ROOT / "corpus" / "land").rglob("source-pack.json"))
    results = [normalize_pack(path) for path in packs]
    changed = [document_id for document_id, was_changed in results if was_changed]
    print(f"Normalized {len(changed)}/{len(results)} governed full-text packs to LF.")


if __name__ == "__main__":
    main()
