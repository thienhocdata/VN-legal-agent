# MVP Architecture

**Status:** Implemented prototype baseline  
**Date:** 2026-07-14

## Components

```text
Chat-first browser client
    -> FastAPI /api/v1
        -> LegalCaseService (workflow and invariants)
            -> SQLite (cases, facts, artifacts, audit events)
            -> Governed demo knowledge adapter
```

The browser exposes one conversational surface. The orchestration endpoint creates the Legal Case invisibly, persists messages, extracts context, asks material questions, and invokes intake, research, evidence, analysis, and review controls. The service layer—not a prompt—enforces provenance transitions, research prerequisites, artifact invalidation, review gating, and audit creation.

## Implemented use-case coverage

- UC-01: create, list, retrieve, and resume tenant-scoped cases.
- UC-02: preserve narrative source and extract a small deterministic set of candidate facts.
- UC-03: create material missing-fact questions and invalidate dependent artifacts after fact changes.
- UC-04: create a minimal issue map and detect dispute review triggers.
- UC-05: require relevant date and locality before research.
- UC-06: create a versioned research session with source identity, location, lifecycle metadata, applicability, snapshot, and explicit coverage gap.
- UC-07: create an evidence map linking proposition, facts, provenance, source version, and citation location.
- UC-08: create dimensional uncertainty and evidence-linked analysis.
- UC-09: create a risk register and ordered action plan with external action disabled.
- UC-10: require the professional-reviewer role to release a gated result.

## Known prototype limits

- Header-based tenant context is demonstrative, not production authentication.
- SQLite is suitable for local evaluation, not the final concurrency or availability target.
- Intake and issue spotting use transparent rules rather than a model adapter.
- The corpus contains metadata examples, not a verified complete legal source collection.
- Local procedure coverage is intentionally unverified.
- No document intelligence, external action, filing draft, provider model, or real-estate platform integration is included.
- Retention, encryption, secrets, rate limiting, observability export, and deployment hardening remain to be designed.

These limits are exposed in the health endpoint, UI, research gaps, and analysis output. They must not be removed merely to make a demonstration appear complete.
