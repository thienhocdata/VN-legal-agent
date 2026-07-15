"""Run the corpus/runtime acceptance gate before evaluating model quality."""

from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import Database
from app.knowledge import KnowledgeRepository
from scripts.activate_corpus import activate_corpus, discover_verified_packs


PILOT_QUERIES = (
    "điều kiện chuyển nhượng quyền sử dụng đất",
    "thế chấp quyền sử dụng đất và sự đồng ý của ngân hàng",
    "hồ sơ đăng ký biến động sang tên tại TP. Hồ Chí Minh",
)


def run_gate() -> dict:
    corpus_root = ROOT / "corpus" / "land"
    packs = discover_verified_packs(corpus_root)
    with tempfile.TemporaryDirectory(prefix="minhlong-release-gate-") as directory:
        database_path = Path(directory) / "runtime.db"
        activation = activate_corpus(
            corpus_root=corpus_root,
            active_database=database_path,
            activate=True,
            relevant_date=date.today().isoformat(),
        )
        repository = KnowledgeRepository(Database(database_path), allow_demo=False)
        queries = []
        for query in PILOT_QUERIES:
            hits, notice = repository.search_by_issues(query, {
                "locality": "TP. Hồ Chí Minh",
                "relevant_date": date.today().isoformat(),
                "event_timeline": [],
            })
            candidates = [
                item for item in hits
                if item.get("applicability") == "candidate"
                and item.get("governance_status") == "full_text_verified"
            ]
            queries.append({
                "query": query,
                "candidate_count": len(candidates),
                "top_locations": [item["location"] for item in candidates[:4]],
                "notice": notice,
            })
        passed = (
            activation["expected_documents"] == activation["imported_documents"]
            and activation["expected_provisions"] == activation["imported_provisions"]
            and activation["runtime_search_passed"]
            and not activation["demo_fallback_used"]
            and all(item["candidate_count"] > 0 for item in queries)
        )
        return {
            "passed": passed,
            "verified_pack_count": len(packs),
            "activation": activation,
            "pilot_queries": queries,
        }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = run_gate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
