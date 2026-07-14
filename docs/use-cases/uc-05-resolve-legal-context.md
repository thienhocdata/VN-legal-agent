# UC-05: Resolve date, jurisdiction, and locality

**Milestone:** Phase 1B - Legal Research  
**Status:** Draft for review

## Goal

Establish the legal context needed to select potentially applicable rules and prevent temporal or locality leakage.

## Main flow

1. For each active issue, the Agent identifies the legally relevant event date or date range, not merely the conversation date.
2. It resolves the governing jurisdiction, administrative level, locality, and legal subject where they may affect the result.
3. It distinguishes substantive event dates, filing dates, decision dates, and current-action dates.
4. It detects possible transitional rules, boundary changes, authority changes, or missing locality coverage.
5. The resolved context and supporting facts are presented for confirmation when material.
6. The Agent creates a versioned research-context record for UC-06.

## Alternate and failure flows

- Unknown event date creates bounded date scenarios or blocks unconditional analysis.
- Unsupported locality prevents claiming a verified local procedure.
- Multiple parcels or events may create multiple research contexts within one case.
- A current procedure may require current rules while substantive rights depend on an earlier date; both contexts are retained.

## Required records

Issue; relevant-date semantics and value; jurisdiction; locality; subject; authority; supporting facts; unresolved dimensions; confirmation; context version.

## Acceptance criteria

- Research cannot silently default to the current date or a default province.
- Nationwide rules and local procedures are explicitly distinguished.
- Each outcome-changing context value links to its factual basis and confirmation status.
- Multiple relevant dates can coexist without overwriting each other.
- Unresolved material context results in conditional output or escalation.

## Evaluation evidence

Temporal boundary cases, amendment and transition scenarios, cross-locality leakage tests, multi-event cases, and unsupported-locality safety tests.

