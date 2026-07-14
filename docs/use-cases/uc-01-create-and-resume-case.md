# UC-01: Create and resume a Legal Case

**Milestone:** Phase 1A - Case Intelligence  
**Status:** Draft for review

## Goal

Create a case independent of any chat or property record, then resume it across sessions without losing provenance, history, access boundaries, or unresolved work.

## Actors and trigger

- Primary: case participant or Minh Long staff.
- Supporting: Legal Agent.
- Trigger: an actor starts a new matter or opens an existing authorized case.

## Preconditions

- The actor has an authenticated or explicitly supported guest context.
- Tenant and role are known before protected case data is accessed.

## Main flow

1. The actor requests a new case and provides a short purpose statement.
2. The Agent creates a globally unique `legal_case_id`, audit record, ownership context, creation time, and initial lifecycle state.
3. Optional external IDs are validated and linked as references; they are not copied as Agent-owned records.
4. The Agent records the purpose statement as `user_provided` or `staff_entered` with actor and timestamp.
5. The Agent presents the case identity, scope notice, privacy notice, current status, and next intake step.
6. On resume, authorization is rechecked and the Agent reconstructs a concise case view from persisted state rather than conversation memory alone.
7. The Agent surfaces unresolved facts, issues, pending confirmations, stale research, and required review.

## Alternate and failure flows

- An invalid or unauthorized external reference is rejected without exposing whether the target record exists.
- An external record becoming unavailable does not invalidate prior attributable snapshots.
- Concurrent changes produce a version conflict; no update silently overwrites newer state.
- A deleted, archived, or retention-restricted case follows the applicable access policy.

## Required records

Case identity and version; tenant and access context; actors; external references; purpose; lifecycle events; conversation references; pending work; audit events.

## Acceptance criteria

- A case can exist with zero properties and can reference multiple properties.
- Resuming from a new session yields the same material state and unresolved items.
- Unauthorized cross-tenant access reveals no case data.
- Every lifecycle and linkage change is attributable, timestamped, and versioned.
- The displayed summary distinguishes stored facts from generated summaries.

## Evaluation evidence

State-reconstruction tests, tenant-isolation tests, concurrency tests, lifecycle-transition tests, and an audit-log completeness check.

