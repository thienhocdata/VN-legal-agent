# Pilot Readiness Report

**Assessment date:** 2026-07-14  
**Decision:** Not yet authorized for real-case legal reliance

## Implemented controls

- Tenant-scoped API-key principals with participant, staff, and professional-reviewer roles.
- Client-supplied tenant, actor, and role values are overridden by the authenticated principal.
- Explicit fact provenance and attributable confirmation transitions.
- Versioned case artifacts, dependency invalidation, audit events, research prerequisites, and professional release gate.
- Governed legal-source registry with effective interval, lifecycle status, locality, official URL, hash, version, and provision location.
- Pilot mode disables demo-source fallback and fails closed when no governed source matches.
- Container manifest, health check, persistent data volume, backup guidance, incident guidance, and release checklist.

## Automated evidence

The current suite contains 12 passing tests covering the end-to-end workflow, unresolved-context research blocking, provenance transitions, role restrictions, tenant isolation, stale artifacts, authentication, identity spoof prevention, temporal applicability, locality normalization, neighboring-locality leakage prevention, and governed-source fail-closed behavior.

Command:

```text
python -m pytest -q
............ [100%]
```

The governed-source evaluation contains five scenario families and currently passes 5/5: current TP.HCM transfer, amended effective date, financial-obligation condition, neighboring-locality isolation, and pre-effective-date rejection.

A pilot-mode HTTP smoke test also passed with authentication required, demo sources disabled, a tenant-scoped case created, TP.HCM context resolved, and five governed research results returned.

## Legal-source audit finding

The earlier prototype contains official PDFs for Law 31/2024/QH15 and provision-level parsed text, but its operational metadata has blank effective dates, `unknown` legal status, absent content hashes, incomplete amendment relationships, and incomplete procedure sources. It is therefore not imported automatically.

Four governed source packs are now included: Law 31/2024/QH15 Article 45, Law 43/2024/QH15 effective-date control, TP.HCM Decision 3279/QĐ-UBND procedure 25, and TP.HCM Decision 1351/QĐ-UBND partial-change control. Their official source files and SHA-256 values are preserved in the repository.

Official government records identify Law 31/2024/QH15 and Law 43/2024/QH15, while Law 43/2024/QH15 records an effective date of 2024-08-01. These findings have been converted into governed source packs; professional sign-off remains required before real-case reliance.

## Remaining release blockers

1. A qualified legal reviewer has not signed the exact source-pack summaries and provision lifecycle interpretation.
2. Evaluation scenarios have not been professionally annotated and quantitative thresholds are not approved.
3. Retention, privacy notice, incident owner, reviewer qualification, and pilot case-volume limits are not approved.
4. Docker packaging has not been smoke-tested because the local Docker daemon was unavailable; the non-container pilot HTTP smoke test passed.
5. SQLite, API-key lifecycle, rate limiting, encryption, monitoring export, and production secret storage need deployment-environment review.

## Next authorization gate

The next gate is a controlled internal pilot using synthetic cases only. It requires a named locality, reviewed source pack, named professional reviewer, zero S0/S1 failures in the approved scenario set, and a successful backup/restore plus container smoke test.
