# Use-Case Traceability and Acceptance Plan

**Version:** 0.1  
**Status:** Draft for review  
**Date:** 2026-07-14  
**Applies to:** Agent Core UC-01 through UC-10

## 1. Purpose

This document proves that the Agent Core use cases cover the approved product capabilities and identifies the evidence required before any capability can be called complete. It is the bridge between product requirements, architecture, implementation backlog, and evaluation design.

## 2. Dependency model

```text
UC-01 Create / resume case
  -> UC-02 Structured intake
      -> UC-03 Clarification and conflicts
          -> UC-04 Legal issue map
              -> UC-05 Legal context resolution
                  -> UC-06 Applicable-law research
                      -> UC-07 Evidence map
                          -> UC-08 Legal analysis
                              -> UC-09 Risk and action plan

UC-10 Professional review can be triggered by UC-03 through UC-09.
New facts, changed source versions, or review decisions can invalidate and reopen downstream artifacts.
```

The dependency is logical rather than a rigid user-interface sequence. Research may reveal a missing fact, analysis may reopen an issue, and professional review may require a new research run. Every backward transition must identify the invalidated dependency and preserve prior versions.

## 3. Product-capability traceability

| Approved capability | Primary use case | Supporting use cases | Required proof |
|---|---|---|---|
| Natural Vietnamese conversation | UC-02 | UC-03, UC-08 | Representative Vietnamese scenario evaluation |
| Controlled fact provenance | UC-02 | UC-01, UC-03, UC-07 | Provenance transition and lineage tests |
| Purposeful clarification | UC-03 | UC-02, UC-04 | Materiality, redundancy, and user-burden evaluation |
| Issue spotting | UC-04 | UC-03, UC-10 | Expert-annotated issue recall and escalation tests |
| Date/locality-aware research | UC-05, UC-06 | UC-04, UC-07 | Temporal, transition, and cross-locality adversarial tests |
| Complete conclusion traceability | UC-07 | UC-06, UC-08 | Claim-support and exact-citation validation |
| Analysis/options/risks separation | UC-08, UC-09 | UC-07 | Structured-output and expert legal review |
| Dimensional uncertainty | UC-08 | UC-03, UC-06, UC-09 | Calibration and harmful-overstatement evaluation |
| Cross-session case memory | UC-01 | All | State reconstruction and stale-artifact tests |
| Document understanding | Phase 2 | UC-02, UC-03 | Explicitly deferred; Agent Core accepts fact-source references only |
| Controlled drafts/checklists | Phase 2 | UC-09 | Explicitly deferred; V1 Core produces an action plan only |
| Professional escalation | UC-10 | UC-03 through UC-09 | Trigger, authorization, package, and release-gate tests |

## 4. Product-boundary traceability

| Boundary | Enforcement point | Required negative test |
|---|---|---|
| Does not replace a professional | UC-08, UC-10 | Reserved/high-risk request cannot bypass review gate |
| Does not guarantee outcomes | UC-08, UC-09 | Prompt pressure cannot produce outcome guarantee |
| Does not invent facts or procedures | UC-02, UC-03, UC-09 | Missing detail remains unknown or becomes verification task |
| Does not hide conflicts | UC-03, UC-06, UC-08 | Conflicting facts/rules remain visible in final artifact |
| Retrieved text is not automatically applicable | UC-05, UC-06 | Relevant but inapplicable provision is rejected |
| Invalid-version law is disclosed | UC-06 | Superseded/not-yet-effective provision cannot be silently relied on |
| Agent inference is not confirmed fact | UC-02 | No automated path from `agent_inferred` to confirmed |
| External action requires confirmation | UC-09 | Tool/action call is blocked without explicit authorization |
| Essential gaps prevent final high-risk conclusion | UC-03, UC-08, UC-10 | Blocking gap produces conditional result or escalation |
| Case privacy is isolated | UC-01, UC-10 | Cross-tenant identifiers cannot disclose content or existence |

## 5. Artifact contracts

Each artifact must have a stable ID, case ID, tenant context, schema version, artifact version, creation actor or agent run, creation time, dependency versions, lifecycle status, and audit history.

| Artifact | Created by | Consumed by | Stale when |
|---|---|---|---|
| Legal Case state | UC-01 | All | Never replaced; version advances |
| Fact set and provenance graph | UC-02 | UC-03 onward | A relied-upon fact is corrected, conflicted, or reclassified |
| Missing-fact/conflict set | UC-03 | UC-04 onward | Relevant answers or evidence arrive |
| Legal issue map | UC-04 | UC-05 onward | Material facts, scope, or issue decisions change |
| Research context | UC-05 | UC-06 onward | Relevant date, locality, jurisdiction, subject, or issue changes |
| Research session and source snapshot | UC-06 | UC-07 onward | Context changes or a governed source update requires revalidation |
| Evidence map | UC-07 | UC-08 onward | Linked fact, rule, source version, or proposition changes |
| Legal analysis | UC-08 | UC-09, UC-10 | Any material upstream dependency changes |
| Risk/action plan | UC-09 | Actor, UC-10 | Analysis, verified procedure, deadline, or actor constraint changes |
| Professional review decision | UC-10 | UC-08, UC-09 | Reviewed dependencies change or reviewer reopens the decision |

Stale artifacts remain readable for audit but cannot be presented as current without a prominent status.

## 6. Acceptance layers

### 6.1 Contract acceptance

- Required fields, enums, relationships, lifecycle transitions, and schema-version behavior pass deterministic tests.
- Invalid provenance, authorization, and artifact-transition requests fail closed.

### 6.2 Component acceptance

- Extraction, clarification, issue spotting, retrieval, applicability, citation, synthesis, and safety components meet task-specific thresholds.
- Component scores do not substitute for end-to-end acceptance.

### 6.3 Scenario acceptance

- A reviewed scenario runs from case creation to a safe current outcome.
- The result is reproducible from stored case, research, source, run, and human-decision snapshots.
- Every material conclusion passes support-chain inspection.

### 6.4 Adversarial acceptance

- Tests include misleading user assertions, prompt injection in source content, obsolete law, wrong locality, absent essential facts, conflicting evidence, source outage, unauthorized access, and pressure to guarantee an outcome.

### 6.5 Operational acceptance

- Latency, cost, availability, retry, timeout, audit completeness, deletion/retention, and incident-observability targets are measured in a production-like environment.

### 6.6 Professional acceptance

- A qualified reviewer evaluates legal correctness, completeness of conditions and exceptions, appropriateness of uncertainty, escalation decisions, and practical executability.

## 7. Severity model

| Severity | Definition | Release effect |
|---|---|---|
| S0 Critical | Privacy breach, unauthorized external action, fabricated authority used materially, or prohibited high-risk output released | Immediate release block |
| S1 High | Wrong applicable law/date/locality, missing material exception, unsupported material conclusion, or missed mandatory escalation | Release block until corrected and regression-covered |
| S2 Medium | Materially inefficient clarification, incomplete but non-harmful issue coverage, weak explanation, or noncritical action-plan defect | Threshold-based release block |
| S3 Low | Style, minor usability, or nonmaterial metadata defect | Tracked; may ship within agreed budget |

Final severity ownership and error budgets require approval in the evaluation specification.

## 8. Minimum scenario families

Before Agent Core release, the evaluation set must include:

1. A straightforward supported matter with complete confirmed facts.
2. A matter with a missing outcome-changing date.
3. A matter where current law differs from law at the relevant event date.
4. A nationwide rule combined with a verified local procedure.
5. An unsupported locality that must not inherit another locality's procedure.
6. Conflicting user statements or conflicting fact sources.
7. A relevant-looking but superseded or not-yet-effective provision.
8. A material exception that changes the leading conclusion.
9. A multi-issue or multi-parcel case.
10. A high-risk case requiring professional review.
11. An out-of-scope legal issue mixed with an in-scope land-law issue.
12. A cross-session case update that invalidates earlier analysis.
13. A cross-tenant access attempt.
14. An attempted external action without confirmation.
15. Source content containing instructions intended to manipulate the Agent.

## 9. Definition of ready for architecture

The use-case package is ready to drive detailed architecture when:

- UC-01 through UC-10 and the global invariants are reviewed;
- first-release scope and locality coverage are selected;
- user/reviewer roles and mandatory escalation triggers are approved;
- shared artifact names and invalidation rules are accepted;
- deferred Phase 2 behavior is not accidentally included in Agent Core commitments;
- evaluation owners and initial severity interpretation are assigned.

## 10. Definition of done for an implemented use case

An implemented use case is done only when its contract tests, positive and negative flows, security controls, observability, evaluation scenarios, regression cases, and documentation all pass the approved thresholds. A demonstration or successful happy-path conversation is not completion evidence.

