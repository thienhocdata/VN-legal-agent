# First-Release Decision Register

**Version:** 0.1  
**Status:** Proposed for approval  
**Date:** 2026-07-14

## 1. Purpose

Product Definition v1.0 intentionally leaves implementation scope choices open. This register proposes a narrow first-release baseline so architecture and evaluation can proceed without silently expanding product scope.

## 2. Proposed decisions

### FR-01: Initial end-to-end matter

**Proposal:** Begin with preparation and preliminary decision support for a common voluntary land-use-right transfer involving an individual household transaction and an existing certificate.

The first vertical slice should cover eligibility questions, material fact intake, rule research, risk identification, and a preparation action plan. It must not submit a transaction, certify legal status, guarantee transfer eligibility, or replace notarization/competent-authority review.

**Reason:** This exercises case intelligence, temporal applicability, legal research, evidence mapping, and practical preparation without requiring dispute resolution as the first production workflow.

### FR-02: Secondary evaluation-only matters

**Proposal:** Use inheritance, certificate-related procedures, land recovery/compensation, land-use conversion, planning, and common disputes as evaluation and architecture stress cases initially, not as supported release claims.

**Reason:** They expose different issue and risk patterns while preventing the first release from claiming unsupported breadth.

### FR-03: Locality coverage

**Proposal:** Select one province or centrally governed municipality for verified local-procedure coverage. Outside that locality, the Agent may explain verified nationwide law but must label local operational details as unverified and escalate or create verification tasks.

**Approval needed:** The business owner must name the initial locality based on Minh Long's actual operating area and access to authoritative local sources.

### FR-04: Core roles

**Proposal:** Support three operational roles:

- `case_participant`: view and contribute to their authorized cases, confirm their own facts;
- `case_staff`: create and prepare authorized tenant cases, add `staff_entered` facts, cannot professionally confirm;
- `professional_reviewer`: review assigned cases, add `professional_confirmed` facts, and release or reject review-gated outputs.

Knowledge administration and evaluation are internal capabilities with separate least-privilege roles, not bundled into professional review.

### FR-05: Document handling boundary

**Proposal:** Agent Core stores document references and manually entered facts but does not claim general document extraction. Automated upload, classification, OCR, extraction, and cross-document conflict detection remain Phase 2.

If a prototype utility is evaluated early, it remains an experimental input channel and cannot change the released capability claim.

### FR-06: External actions

**Proposal:** No external filing, submission, booking, message, payment, or authority-system integration in the first release. The product produces preparation guidance only.

### FR-07: Mandatory review baseline

**Proposal:** Require professional review when any of the following is present:

- active dispute, complaint, litigation, enforcement, or imminent irreversible deadline;
- suspected fraud, forged/invalid document, coercion, incapacity, or vulnerable participant;
- conflicting authoritative rules not safely resolved;
- unsupported locality-specific procedure material to the recommendation;
- missing essential fact or source combined with high potential impact;
- material issue outside approved release scope;
- request for a definitive title, validity, litigation, tax, valuation, notarization, or authority outcome;
- Agent safety policy or dimensional uncertainty crosses an approved threshold.

The evaluation specification must turn this baseline into deterministic and model-evaluated gates.

### FR-08: Output boundary

**Proposal:** The first release may produce:

- a structured case summary;
- missing and conflicting fact list;
- legal issue map;
- research and evidence view;
- bounded analysis with alternatives and uncertainty;
- risk register;
- preparation checklist and action plan;
- professional review package.

It does not produce a filing-ready legal instrument or represent that any draft is approved by a professional.

### FR-09: Source baseline

**Proposal:** Material legal claims must rely on governed official sources or an approved authoritative source hierarchy. Discovery through secondary material is permitted, but the evidence chain must terminate at an approved source with a reproducible snapshot and lifecycle metadata.

The source-governance specification must define authority ranking, snapshot policy, amendment modeling, correction procedure, and outage behavior.

### FR-10: Release claim

**Proposal:** Describe the first release as a controlled pilot for a named transfer-preparation workflow and named locality. Do not market it as a general Vietnamese land-law adviser.

## 3. Decisions still requiring owner input

1. The named initial locality.
2. Whether the initial transfer scenario includes organizations or only individuals/households.
3. Which authority/source systems are operationally accessible and acceptable for the chosen locality.
4. Who may act as professional reviewer and what qualification/authorization evidence is required.
5. Pilot audience, case volume, data-retention period, and incident owner.
6. Quantitative release thresholds, latency target, and operating-cost envelope.

## 4. Approval effect

Approval of this register authorizes detailed architecture and evaluation design for the selected pilot. It does not alter Product Definition v1.0 and does not authorize production release or external legal actions.

