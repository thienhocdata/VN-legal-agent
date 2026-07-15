# Pilot Readiness Report

**Assessment date:** 2026-07-15
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

The current suite contains 49 passing tests covering the end-to-end workflow, six-gate decision output, official-source promotion controls, temporal and locality applicability, historical comparison, neighboring-locality isolation, authentication, provenance, and evidence-backed behavior when the language-model quota is unavailable.

Command:

```text
python -m pytest -q
................................................. [100%]
```

The governed-source evaluation contains seven scenario families and passes 7/7: current TP.HCM transfer, notarization, mortgage/security registration, TP.HCM change registration, pre-effective-date protection, 2013/current-law comparison, and neighboring-locality isolation.

A pilot-mode HTTP smoke test also passed with authentication required, demo sources disabled, a tenant-scoped case created, TP.HCM context resolved, and five governed research results returned. The chat-first HTTP smoke test passed with the conversation page rendered, a hidden case created, a complete answer returned, and seven citations attached.

## Legal-source audit finding

The active **Giao dịch** package now contains 18/18 mandatory full-text-verified document packs, 1,939 official PDF pages, 2,450 articles, and 17,356 article/clause/point records. It includes the original Law 45/2013/QH13, consolidated 21/VBHN-VPQH for the 2019–31/07/2024 interval, consolidated current land law, implementing decrees and resolution, Civil Code, notarization, marriage/family, real-estate business, housing, credit-institution, security-registration, and TP.HCM procedure sources.

Promotion requires official-source identity, artifact hash matching, first/middle/last-page visual review, complete article sequence, no duplicate nested provision candidates, explicit effectivity/lifecycle metadata, and machine-assisted reviewer attestation. This is source governance evidence, not qualified-lawyer sign-off.

Overall package readiness is **1/10**, not 10/10. Certificate is 7/9 verified mandatory documents; the other packages remain incomplete and fail closed rather than borrowing unsupported procedure, finance, planning, dispute, or locality details.

## Remaining release blockers

1. A qualified legal reviewer has not signed the exact source-pack summaries and provision lifecycle interpretation.
2. Evaluation scenarios have not been professionally annotated and quantitative thresholds are not approved.
3. Retention, privacy notice, incident owner, reviewer qualification, and pilot case-volume limits are not approved.
4. Docker packaging has not been smoke-tested because the local Docker daemon was unavailable; the non-container pilot HTTP smoke test passed.
5. SQLite, API-key lifecycle, rate limiting, encryption, monitoring export, and production secret storage need deployment-environment review.

## Next authorization gate

The next gate is a controlled internal pilot using synthetic cases only. It requires a named locality, reviewed source pack, named professional reviewer, zero S0/S1 failures in the approved scenario set, and a successful backup/restore plus container smoke test.
