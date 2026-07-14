from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from app.config import Settings
from app.coverage import normalize_locality
from app.database import Database
from app.knowledge import KnowledgeRepository


scenarios = json.loads((root / "data" / "evaluation" / "pilot_scenarios.json").read_text(encoding="utf-8"))
repo = KnowledgeRepository(Database(Settings.load().database_path), allow_demo=False)
results = []
for scenario in scenarios:
    locality, _ = normalize_locality(scenario["locality"])
    hits, gap = repo.search(scenario["query"], {"relevant_date": scenario["relevant_date"], "locality": locality})
    candidates = {hit["source_id"] for hit in hits if hit["applicability"] == "candidate"}
    expected = set(scenario.get("expected_candidate_sources", []))
    forbidden = set(scenario.get("forbidden_candidate_sources", []))
    passed = expected <= candidates and not (forbidden & candidates)
    results.append({"id": scenario["id"], "passed": passed, "candidates": sorted(candidates), "gap": gap})

report = {"passed": sum(r["passed"] for r in results), "total": len(results), "results": results}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["passed"] == report["total"] else 1)

