# UC-10: Escalate and incorporate professional review

**Milestone:** Phase 1C - Analysis and Action  
**Status:** Draft for review

## Goal

Stop unsafe autonomous completion, provide a useful review package, and incorporate an authorized professional decision without erasing prior Agent reasoning.

## Escalation triggers

Candidate triggers include high impact or irreversibility; imminent deadline; dispute or litigation posture; conflicting authoritative sources; unsupported locality; missing essential facts; suspected fraud or document irregularity; vulnerable participant; out-of-scope law; low evidence completeness; or a request for a reserved professional act.

Final mandatory triggers and severity levels require approval before implementation.

## Main flow

1. A safety gate detects and records the trigger, severity, affected issues, and blocked outputs.
2. The Agent explains in plain language why review is required and provides safe interim steps where supported.
3. It creates a review package containing objectives, chronology, facts by provenance, conflicts, missing facts, issue map, research context, source snapshots, evidence map, draft analysis, uncertainty, risks, and focused review questions.
4. Only an authorized reviewer can accept the assignment and access the package.
5. The reviewer may confirm, correct, add, reject, or request information; every action is attributable and reasoned.
6. Professional confirmations use `professional_confirmed` while preserving earlier fact states and Agent outputs.
7. A new analysis or action-plan version incorporates the decision and clearly identifies what changed.
8. The case remains review-required until explicit authorized release or closure.

## Alternate and failure flows

- No reviewer available: preserve the queue state, communicate limitation, and do not release blocked conclusions.
- Reviewer disagreement: retain both decisions, authority context, and escalation path.
- New facts after approval invalidate affected review decisions and reopen the gate.
- Access revocation immediately blocks further review access without deleting audit history.

## Required records

Trigger and severity; safety decision; review package version; assignee and authorization; review actions and rationale; professional confirmations; release decision; affected output versions; audit trail.

## Acceptance criteria

- Mandatory triggers reliably prevent release of prohibited final outputs.
- The review package is sufficient to inspect every material claim without reconstructing chat history manually.
- Reviewer changes never overwrite original facts, sources, Agent analysis, or prior decisions.
- Only authorized reviewers can confirm professionally or release the gate.
- Changed dependencies reopen affected review and mark outputs stale.

## Evaluation evidence

Trigger recall and false-release rate, authorization tests, package-completeness rubric, reviewer-action audit tests, disagreement scenarios, and stale-approval invalidation tests.

