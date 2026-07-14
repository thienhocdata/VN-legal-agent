# UC-04: Identify and maintain legal issues

**Milestone:** Phase 1A - Case Intelligence  
**Status:** Draft for review

## Goal

Create a reviewable issue map that guides research without mistaking issue hypotheses for legal conclusions.

## Main flow

1. The Agent reviews confirmed and unconfirmed facts, objectives, dates, actors, parcel context, and conflicts.
2. It creates candidate legal issues with a plain-language label, legal-domain classification, triggering facts, missing facts, and rationale.
3. Issues are marked as active, possible, excluded, resolved, or review-required.
4. The Agent records dependencies between issues and distinguishes primary issues from secondary or procedural ones.
5. The actor receives a concise explanation of what will be researched and what cannot yet be determined.
6. New facts or research may revise the map; every revision preserves history and rationale.

## Alternate and failure flows

- An out-of-scope issue is retained and routed to escalation rather than discarded.
- A potentially urgent deadline or irreversible action creates a high-priority safety flag.
- Mutually exclusive issue hypotheses remain open until supporting facts resolve them.

## Required records

Issue ID; classification; description; triggering facts; missing facts; dependencies; scope status; risk flags; lifecycle and revision history.

## Acceptance criteria

- Each issue links to case facts and explains why it is present.
- The Agent does not state that an issue is legally resolved before validated research and analysis.
- Material procedural and counter-issues are included in evaluation scenarios.
- Out-of-scope and urgent issues produce the correct escalation behavior.
- Issue-map changes are attributable to new facts, research, or human review.

## Evaluation evidence

Expert-annotated issue-spotting set measuring material recall, harmful over-identification, procedural coverage, rationale quality, and escalation correctness.

