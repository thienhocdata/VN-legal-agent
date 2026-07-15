from __future__ import annotations

"""Compatibility entry point for governed corpus activation."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings
from scripts.activate_corpus import activate_corpus


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = activate_corpus(
        corpus_root=ROOT / "corpus" / "land",
        active_database=Path(Settings.load().database_path),
        report_path=ROOT / "data" / "corpus-activation-report.json",
        activate=True,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
