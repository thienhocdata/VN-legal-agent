# UC-08: Produce evidence-linked legal analysis

**Milestone:** Phase 1C - Analysis and Action  
**Status:** Draft for review

## Goal

Provide understandable decision support that separates facts, rules, analysis, alternatives, uncertainty, and professional judgment.

## Main flow

1. The Agent verifies that issue, context, research, and evidence-map prerequisites are current.
2. It states the understood objective and material confirmed, unconfirmed, and assumed facts.
3. For each issue, it explains applicable rules and analyzes how their conditions and exceptions map to case facts.
4. It presents the leading conclusion, reasonable alternative interpretations, counter-considerations, and consequences.
5. Each material conclusion exposes its fact and legal-evidence chain.
6. Uncertainty is reported separately for factual completeness, source coverage, temporal/locality resolution, applicability, and legal interpretation.
7. The Agent applies scope and review gates before releasing the analysis.

## Alternate and failure flows

- Missing essential support yields conditional analysis, a request for information, or escalation—not a final conclusion.
- Conflicting authority or high-risk interpretation triggers professional review.
- If facts change, affected analysis is marked stale and must be regenerated with a new version.

## Required records

Analysis version; objectives; relied-upon facts and assumptions; issue conclusions; alternatives; uncertainty dimensions; evidence links; safety decision; generation/run metadata.

## Acceptance criteria

- Fact, rule, application, conclusion, risk, and recommendation are distinguishable.
- Every material conclusion passes evidence-map validation.
- The output does not guarantee outcomes or conceal material exceptions and conflicts.
- Unconfirmed and inferred facts are visibly qualified.
- Legal correctness and practical usefulness are scored separately.

## Evaluation evidence

Professional review rubric, applicability and exception tests, citation-entailment checks, uncertainty-calibration set, harmful-overstatement rate, and version-staleness tests.

