# UC-02: Conduct structured conversational intake

**Milestone:** Phase 1A - Case Intelligence  
**Status:** Draft for review

## Goal

Turn a natural Vietnamese account into a structured, reviewable case record without presenting inferred information as established fact.

## Actors and trigger

- Primary: case participant or Minh Long staff.
- Trigger: the actor describes a land-law situation or adds information to a case.

## Preconditions

- An authorized Legal Case exists.
- The current speaker and input channel are identifiable.

## Main flow

1. The Agent receives free text and preserves the original utterance as immutable source material.
2. It extracts candidate people, organizations, parcels, locations, dates, events, documents, objectives, and constraints.
3. Each extracted item links to the source span, extraction method, actor, capture time, and status.
4. Direct statements are recorded as `user_provided` or `staff_entered`; derived interpretations are recorded separately as `agent_inferred`.
5. The Agent shows a concise structured recap and asks the actor to correct or confirm only material items.
6. Explicit confirmations create `user_confirmed` or `professional_confirmed` events while preserving prior history.
7. The Agent records ambiguities and contradictions rather than forcing a single value.

## Alternate and failure flows

- If the speaker is reporting another person's statement, both reporter and asserted source are retained.
- Relative dates and informal locations remain unresolved until normalized and confirmed.
- Sensitive or irrelevant information is minimized or flagged under data policy.
- Extraction failure preserves the original input and creates a reviewable processing error.

## Required records

Source utterance; source spans; structured facts; entities and events; provenance history; extraction run and model/tool version; confirmations; ambiguity and conflict records.

## Acceptance criteria

- Every structured fact can be traced to source text or an explicit inference record.
- No `agent_inferred` item is displayed or stored as confirmed.
- Corrections append history rather than erase the prior assertion.
- The recap clearly separates confirmed, unconfirmed, inferred, missing, and conflicting information.
- Reprocessing the utterance does not duplicate logically identical facts without lineage.

## Evaluation evidence

Vietnamese intake corpus with gold fact spans, provenance-state tests, correction-history tests, extraction calibration by fact type, and privacy-minimization review.

