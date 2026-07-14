# UC-03: Clarify missing and conflicting facts

**Milestone:** Phase 1A - Case Intelligence  
**Status:** Draft for review

## Goal

Identify facts that can materially change the legal analysis, ask purposeful questions, and preserve unresolved conflicts without exhausting the user.

## Main flow

1. The Agent evaluates the current facts against issue-specific information requirements.
2. It classifies gaps as blocking, material-but-nonblocking, or optional.
3. Questions are ranked by expected effect on issue selection, applicable law, risk, or next action.
4. The Agent asks a small, coherent set of plain-language questions and explains why sensitive or difficult information matters.
5. Answers are processed through UC-02 provenance rules.
6. Conflicting assertions are linked in a conflict record; neither value is silently selected.
7. The Agent resolves a conflict only through attributable evidence, explicit human confirmation, or professional review.
8. If a blocking fact cannot be obtained, the downstream limitation and escalation state are recorded.

## Alternate and failure flows

- The actor may say “unknown”; the Agent must not repeatedly ask without new reason.
- A document and user statement may disagree; both remain visible with source strength and confirmation state.
- Questions outside the supported scope are omitted or redirected to review.
- If urgency prevents complete intake, the Agent provides only safe, conditional guidance.

## Required records

Missing-fact candidates; materiality and priority; question rationale; asked/answered history; conflict sets; resolution events; downstream limitations.

## Acceptance criteria

- Every clarification question maps to a material fact requirement or conflict.
- Known information is not requested again unless its reliability or applicability changed.
- The system accepts “unknown” and records the effect on analysis.
- Conflict resolution retains both original assertions and the resolving evidence or actor.
- Blocking gaps prevent an unconditional final conclusion.

## Evaluation evidence

Question relevance and redundancy scores, information-gain scenarios, conflict-resolution tests, user-burden measures, and safety tests for missing essential facts.

