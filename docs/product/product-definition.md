# Product Definition

**Version:** 1.0
**Status:** Approved
**Approved:** 2026-07-14
**Product:** Minh Long Legal Agent
**Initial legal domain:** Vietnamese land law

## 1. Product statement

Minh Long Legal Agent is an AI-assisted legal decision-support platform that helps non-expert individuals and small businesses analyze, understand, and prepare Vietnamese land-law matters. It combines natural conversation with structured case management, controlled legal research, verifiable citations, document support, and escalation to a qualified professional.

It is a real product intended for continued operation and integration, not a retrieval demonstration or a substitute for a lawyer.

## 2. Long-term ecosystem

The agent is built first as an independently deployable legal service with a minimal operational console. It will later become a core capability of the Minh Long company website, alongside real-estate brokerage, land procedures, cadastral measurement, design, and construction services.

Information from the website research provides business context but does not constrain the agent architecture. Both products may evolve so the final ecosystem works as one coherent product.

The final product vision is an integrated real-estate service platform combining brokerage, case and document management, design and construction consulting, and AI-assisted legal support.

The Legal Agent is a separately bounded service. It can operate independently or be called from property, brokerage, design, construction, and document-management workflows.

## 3. Primary users

- Individuals dealing with land-use rights, certificates, transfers, inheritance, disputes, planning, recovery, compensation, or administrative procedures.
- Small businesses needing initial land-law research and case preparation.
- Minh Long staff or legal professionals reviewing cases and continuing work that exceeds the agent's authority.

## 4. Unit of work

The primary unit is a **Legal Case**, not a chat session.

A case may contain:

- user statements and confirmed facts;
- people, organizations, land parcels, locations, and relevant dates;
- uploaded and extracted documents;
- missing or conflicting information;
- identified legal issues;
- research runs and applicable legal provisions;
- evidence supporting each material conclusion;
- analysis, options, risks, and recommended next steps;
- generated documents and professional-review status;
- multiple conversations over time.

A Legal Case may reference zero, one, or multiple external properties. It may also reference an external user, organization, brokerage request, or other business workflow, but none of those references is required for the case to exist.

The agent owns its legal-case state. It does not become the system of record for platform users, companies, properties, listings, payments, or service requests.

Every fact and evidence record must preserve provenance, including source type, source identifier, capture or extraction method, confirmation status, and recorded time. Fact provenance uses the following controlled states:

- `user_provided`;
- `document_extracted`;
- `staff_entered`;
- `agent_inferred`;
- `user_confirmed`;
- `professional_confirmed`.

An `agent_inferred` fact must never become confirmed automatically. Confirmation is an explicit, attributable action, and the system must preserve the prior provenance history rather than overwrite it.

## 5. Target capabilities

The product should be able to:

1. Conduct a natural Vietnamese conversation about a legal situation.
2. Separate user-provided, document-extracted, staff-entered, agent-inferred, user-confirmed, and professional-confirmed information.
3. Ask purposeful clarification questions rather than returning a generic answer too early.
4. Identify legal issues and explicitly record unresolved issues.
5. Research official legal sources by jurisdiction, locality, applicable date, and provision-level validity.
6. Make every material analytical conclusion traceable through the complete chain: conclusion → applicable facts → legal rule → source version → exact citation location.
7. Clearly separate legal analysis, options, risks, and practical recommendations.
8. Express uncertainty by dimension instead of presenting a misleading single percentage.
9. Maintain case memory across multiple sessions while preserving provenance.
10. Read supported documents and expose extraction uncertainty.
11. Generate controlled, schema-based drafts and checklists.
12. Escalate high-risk, ambiguous, or out-of-scope cases for professional review.

## 6. Initial production scope

The first production domain is Vietnamese land law. Breadth will be constrained until depth, source quality, evaluation, and operational safety meet the acceptance criteria.

Candidate subdomains will be selected through the use-case specification rather than assumed here. Possible areas include land-use-right certificates, transfers, inheritance, administrative procedures, land recovery and compensation, planning information, land-use conversion, and common disputes.

The current delivery scope is the Legal Agent Core packaged behind a stable API and supported by a minimal internal console. The console exists to create cases, conduct intake, upload documents, inspect extracted facts and issues, review evidence and citations, view action plans, and evaluate agent behavior. It is not the final commercial website.

The system must distinguish nationwide legal rules from locality-specific procedures. No legal rule or procedure may be treated as applicable without resolving jurisdiction, locality, and relevant date where those factors may change the result. Rules from one locality must never be generalized to another without an independently verified legal basis.

## 7. Product boundaries

The agent must not:

- claim to replace a lawyer, notary, competent authority, or licensed professional;
- guarantee an administrative, litigation, transaction, or financial outcome;
- invent facts, legal provisions, document contents, fees, deadlines, or local procedures;
- hide conflicting sources or unresolved uncertainty;
- treat retrieved text as automatically applicable law;
- use an expired, superseded, or not-yet-effective provision without detecting and clearly disclosing its status;
- treat an agent inference as a confirmed fact;
- perform an external action without explicit confirmation from the user or an authorized human actor;
- provide a final high-risk conclusion when essential facts or sources are missing;
- expose private case data across users or organizations.

## 8. First-release non-goals

The first release will not:

- support every field of Vietnamese law;
- support every province or municipality;
- submit administrative procedures or legal filings automatically;
- replace professional legal review;
- analyze every possible document type;
- operate a lawyer marketplace;
- provide a native mobile application;
- automatically value real estate;
- provide a separate commercial landing page, billing system, or marketplace for the Agent.

## 9. Quality model

Completion is demonstrated by evidence, not by the number of modules implemented. Evaluation must cover at least:

- factual understanding and provenance;
- clarification quality;
- issue spotting;
- retrieval recall and legal-source validity;
- temporal validity and effective-date correctness;
- locality and jurisdiction validity;
- applicability correctness for the relevant facts and legal subject;
- completeness of material conditions, exceptions, and conflicting rules;
- citation correctness and claim-to-evidence support;
- legal correctness, including analysis quality and counter-considerations;
- practical usefulness, including action-plan executability;
- uncertainty calibration;
- safety and escalation behavior;
- case-memory consistency;
- document extraction and drafting correctness;
- latency, cost, security, privacy, and operational reliability.

## 10. Technical direction

The local development machine will run application code, tests, case workflows, and development data. Strong foundation models and compute-heavy workloads will use provider APIs or cloud/GPU infrastructure. The architecture must avoid dependence on one model vendor and provide cost, timeout, retry, and fallback controls.

GPU rental is an implementation option, not a product requirement. It will be used only when measurement shows that local embedding, reranking, OCR, evaluation, or model adaptation benefits from it.

The agent maintains its own operational database for legal cases, facts, missing facts, case documents, legal issues, research sessions, agent runs, evidence, citations, action plans, generated documents, and evaluation logs.

Integration records use external identifiers such as `tenant_id`, `user_id`, `property_id`, and business-request IDs. The agent stores only reference identifiers and justified point-in-time snapshots. It must not copy complete User or Property records from the future main platform.

The legal knowledge architecture must support document versioning, effective-date resolution, amendment and replacement relationships, provision-level lifecycle status, and reproducible source snapshots. Retrieval relevance alone is never sufficient to establish that a rule applies.

## 11. Relationship to the prototype

The previous RAG system may contribute carefully reviewed source data, ingestion utilities, or regression tests. Its chat-centered architecture and existing quality scores do not define this product and will not be migrated wholesale.

## 12. Open implementation decisions

Approval of this Product Definition fixes the product identity, boundaries, and quality principles. The following implementation choices remain to be specified and approved in their corresponding design artifacts:

- The first eight to ten end-to-end use cases.
- The initial supported localities and verified local-procedure coverage.
- Supported document types in the first release.
- Conditions that require professional review.
- User roles and access boundaries for the first operational release.
- Model-provider strategy and acceptable operating-cost envelope.
- Quantitative release thresholds for each evaluation dimension.

## 13. Delivery roadmap

### Phase 1 — Agent Core

#### Phase 1A — Case Intelligence

- Legal Case model and lifecycle.
- Conversational intake and structured facts with provenance.
- Missing-fact detection and purposeful clarification.
- Legal issue spotting.

#### Phase 1B — Legal Research

- Multi-document research and retrieval.
- Jurisdiction, locality, and relevant-date resolution.
- Source versioning and provision-level applicability checks.
- Evidence and exact citation-location mapping.

#### Phase 1C — Analysis and Action

- Evidence-linked analysis and answer synthesis.
- Risks, exceptions, alternative interpretations, and action plans.
- Escalation behavior and end-to-end evaluation.

### Phase 2 — Document Intelligence

- Upload and classify supported legal documents.
- Extract facts with provenance and confidence.
- Detect conflicts across statements and documents.
- Link documents to facts and legal issues.
- Produce document checklists.

### Phase 3 — Agent API

- Stable and versioned API contracts.
- Streaming responses.
- Service-to-service authentication and authorization.
- Audit logs, events or webhooks, and API documentation.

### Phase 4 — Main Real Estate Platform

- Users and organizations.
- Properties and listings.
- Brokerage and design/construction requests.
- CRM and administration.

### Phase 5 — Integration

- Create or link Legal Cases from business workflows.
- Reference users, organizations, properties, documents, and requests by ID.
- Expose legal-check, transfer-analysis, title-transfer preparation, construction-condition, and dispute-analysis workflows.

## 14. Change control

Changes to the approved product identity, boundaries, primary users, unit of work, or safety principles require a new reviewed version of this document.

Implementation details may evolve through separate use-case, architecture, data, security, and evaluation specifications without reopening this Product Definition unless they materially change the approved product scope.
