# UC-06: Research and validate applicable law

**Milestone:** Phase 1B - Legal Research  
**Status:** Draft for review

## Goal

Find authoritative legal material and determine whether each provision is potentially applicable to the issue-specific context.

## Main flow

1. The Agent creates a research plan from active issues and the versioned legal context.
2. It searches governed official-source collections using multiple query formulations and provision relationships.
3. Candidate provisions are retrieved with document identity, source authority, version, effective interval, lifecycle status, and exact location.
4. The Agent follows amendments, replacements, implementing instruments, referenced provisions, and relevant local instruments.
5. Each candidate receives an applicability assessment covering date, jurisdiction, locality, subject, conditions, exceptions, and conflict priority.
6. Unsupported or conflicting points generate further research or a recorded research gap.
7. The complete query, filters, tool versions, source snapshots, results, exclusions, and rationale are stored as a reproducible research session.

## Alternate and failure flows

- Expired, superseded, or not-yet-effective text may be retained for history but is clearly labeled and not silently applied.
- An unofficial source may assist discovery but cannot be the sole support where an official source is required and obtainable.
- Source outage or incomplete collection is disclosed as source uncertainty.
- Conflicting instruments are escalated when hierarchy or applicability cannot be safely resolved.

## Required records

Research plan; queries and filters; retrieved and excluded provisions; source/version metadata; effective-date calculations; relationships; applicability assessments; snapshots; gaps.

## Acceptance criteria

- Every relied-upon provision has stable identity, version, exact location, and source snapshot.
- Retrieval relevance is separate from applicability status.
- Material conditions, exceptions, amendments, and implementing provisions are actively checked.
- The same recorded session can reproduce the relied-upon source set.
- Research gaps are visible to downstream analysis and cannot be hidden by fluent synthesis.

## Evaluation evidence

Provision recall, exact-location precision, temporal/locality correctness, exception completeness, source-authority compliance, reproducibility, and adversarial superseded-law tests.

