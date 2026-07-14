# UC-07: Build claim-to-evidence traceability

**Milestone:** Phase 1B - Legal Research  
**Status:** Draft for review

## Goal

Build the explicit factual and legal support graph required for later conclusions and expose unsupported or contradictory propositions.

## Main flow

1. The Agent creates candidate analytical propositions for each active issue without yet presenting them as final conclusions.
2. Each proposition links to the facts it assumes, including provenance and confirmation state.
3. It links to applicable rules through source version and exact citation location.
4. Support type is classified as direct, conditional, interpretive, contrary, or contextual.
5. Contradictory facts, counter-rules, exceptions, and missing links are attached to the same proposition.
6. A completeness check blocks unsupported material propositions from final synthesis.
7. The resulting evidence map is stored as a versioned artifact tied to case and research snapshots.

## Required records

Propositions; fact links; provision links; citation spans; support type and strength; contrary evidence; gaps; validation result; artifact version.

## Acceptance criteria

- Every material proposition traverses the full required traceability chain.
- A citation to a document generally is insufficient when an exact provision location exists.
- Facts retain provenance and confirmation status in the evidence view.
- Contrary evidence and exceptions appear alongside supporting material.
- Changing a material fact or source invalidates affected links and marks downstream outputs stale.

## Evaluation evidence

Claim-support precision, citation entailment, citation-location accuracy, unsupported-claim rate, counter-evidence coverage, and stale-dependency tests.

