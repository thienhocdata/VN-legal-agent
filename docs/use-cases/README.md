# Agent Core Use-Case Specification

**Version:** 0.1
**Status:** Draft for review
**Date:** 2026-07-14
**Scope:** Phase 1A-1C

## Purpose

This specification translates Product Definition v1.0 into ten end-to-end behaviors that can be designed, implemented, evaluated, and accepted independently. It defines observable product outcomes, not model prompts or framework choices.

## Global invariants

Every use case must preserve these rules:

1. The Legal Case, not a chat session, is the unit of work.
2. Every fact and item of evidence retains source, method, status, actor, and time. `agent_inferred` never becomes confirmed automatically.
3. No potentially outcome-changing rule is applied before relevant date, jurisdiction, and locality are resolved or explicitly marked unresolved.
4. Every material conclusion is traceable through conclusion -> applicable facts -> legal rule -> source version -> exact citation location.
5. Retrieved text is not automatically applicable law. Effective status, scope, subject, conditions, exceptions, and conflicts must be checked.
6. Uncertainty is expressed by dimension. Missing facts, weak sources, conflicting evidence, and interpretive uncertainty are not collapsed into one confidence score.
7. High-risk, materially incomplete, unsupported, or out-of-scope matters are escalated. The Agent does not replace an authorized professional.
8. No external action occurs without explicit confirmation by the user or an authorized human actor.
9. All material state transitions and human confirmations are attributable and auditable.
10. Tenant and case boundaries are enforced in every read, write, research, and review operation.

## Use-case catalogue

| ID | Milestone | Use case | Primary outcome |
|---|---|---|---|
| [UC-01](uc-01-create-and-resume-case.md) | 1A | Create and resume a Legal Case | Persistent, correctly scoped case state |
| [UC-02](uc-02-structured-intake.md) | 1A | Conduct structured conversational intake | Provenance-preserving fact record |
| [UC-03](uc-03-clarify-and-resolve-conflicts.md) | 1A | Clarify missing and conflicting facts | Material gaps made explicit and prioritized |
| [UC-04](uc-04-identify-legal-issues.md) | 1A | Identify and maintain legal issues | Reviewable issue map without premature conclusions |
| [UC-05](uc-05-resolve-legal-context.md) | 1B | Resolve date, jurisdiction, and locality | Research context safe enough for rule selection |
| [UC-06](uc-06-research-applicable-law.md) | 1B | Research and validate applicable law | Reproducible, version-aware research record |
| [UC-07](uc-07-build-evidence-map.md) | 1B | Build claim-to-evidence traceability | Exact support chain for material propositions |
| [UC-08](uc-08-produce-legal-analysis.md) | 1C | Produce evidence-linked legal analysis | Bounded analysis with alternatives and uncertainty |
| [UC-09](uc-09-produce-action-plan.md) | 1C | Produce risks and an executable action plan | Practical, ordered next steps with dependencies |
| [UC-10](uc-10-escalate-for-professional-review.md) | 1C | Escalate and incorporate professional review | Safe handoff with an auditable review decision |

## Shared roles

- **Case participant:** provides information and receives decision support.
- **Minh Long staff:** assists intake and operational case preparation.
- **Reviewing professional:** reviews matters requiring qualified judgment or authority.
- **Legal Agent:** orchestrates case intelligence, research, analysis, and safety controls.
- **Knowledge administrator:** governs legal sources and their lifecycle metadata.
- **Evaluator:** runs reviewed scenarios and records quality evidence.

## Shared lifecycle

`draft -> intake_in_progress -> research_ready -> research_in_progress -> analysis_ready -> review_required | action_ready -> closed`

A case may move backward when facts change, evidence conflicts, a source version changes, or review reopens an issue. Closing a case does not delete its history.

## Cross-use-case acceptance gate

An end-to-end scenario passes only when the final output can be reproduced from the stored case snapshot, research snapshot, source versions, agent-run record, and human decisions. A fluent answer without this record fails acceptance.

Detailed requirement coverage, artifact dependencies, severity levels, and scenario families are defined in the [Traceability and Acceptance Plan](traceability-and-acceptance.md).

## Items requiring approval before implementation

- First-release land-law subdomains and representative scenario set.
- Initially supported provinces or municipalities.
- Supported participant and staff roles, including authorization boundaries.
- Mandatory professional-review triggers and response-time expectations.
- Quantitative quality thresholds and the severity model for evaluation failures.
- Retention, deletion, and redaction policies for case data and research snapshots.
