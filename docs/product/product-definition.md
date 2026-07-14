# Product Definition

**Status:** Draft for joint review
**Product:** Minh Long Legal Agent
**Initial legal domain:** Vietnamese land law

## 1. Product statement

Minh Long Legal Agent is an AI-assisted legal case platform that helps non-expert individuals and small businesses understand and prepare Vietnamese land-law matters. It combines natural conversation with structured case management, controlled legal research, verifiable citations, document support, and escalation to a qualified professional.

It is a real product intended for continued operation and integration, not a retrieval demonstration or a substitute for a lawyer.

## 2. Long-term ecosystem

The agent is built first as a strong standalone product. It will later become a core capability of the Minh Long company website, alongside real-estate brokerage, land procedures, cadastral measurement, design, and construction services.

Information from the website research provides business context but does not constrain the agent architecture. Both products may evolve so the final ecosystem works as one coherent product.

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

## 5. Target capabilities

The product should be able to:

1. Conduct a natural Vietnamese conversation about a legal situation.
2. Separate user-provided, document-extracted, agent-inferred, and user-confirmed information.
3. Ask purposeful clarification questions rather than returning a generic answer too early.
4. Identify legal issues and explicitly record unresolved issues.
5. Research official legal sources by jurisdiction, locality, applicable date, and provision-level validity.
6. Link factual premises and legal evidence to individual analytical conclusions.
7. Clearly separate legal analysis, options, risks, and practical recommendations.
8. Express uncertainty by dimension instead of presenting a misleading single percentage.
9. Maintain case memory across multiple sessions while preserving provenance.
10. Read supported documents and expose extraction uncertainty.
11. Generate controlled, schema-based drafts and checklists.
12. Escalate high-risk, ambiguous, or out-of-scope cases for professional review.

## 6. Initial production scope

The first production domain is Vietnamese land law. Breadth will be constrained until depth, source quality, evaluation, and operational safety meet the acceptance criteria.

Candidate subdomains will be selected through the use-case specification rather than assumed here. Possible areas include land-use-right certificates, transfers, inheritance, administrative procedures, land recovery and compensation, planning information, land-use conversion, and common disputes.

## 7. Product boundaries

The agent must not:

- claim to replace a lawyer, notary, competent authority, or licensed professional;
- guarantee an administrative, litigation, transaction, or financial outcome;
- invent facts, legal provisions, document contents, fees, deadlines, or local procedures;
- hide conflicting sources or unresolved uncertainty;
- treat retrieved text as automatically applicable law;
- provide a final high-risk conclusion when essential facts or sources are missing;
- expose private case data across users or organizations.

## 8. Quality model

Completion is demonstrated by evidence, not by the number of modules implemented. Evaluation must cover at least:

- factual understanding and provenance;
- clarification quality;
- issue spotting;
- retrieval recall and legal-source validity;
- citation correctness and claim-to-evidence support;
- analysis quality and counter-considerations;
- uncertainty calibration;
- safety and escalation behavior;
- case-memory consistency;
- document extraction and drafting correctness;
- latency, cost, security, privacy, and operational reliability.

## 9. Technical direction

The local development machine will run application code, tests, case workflows, and development data. Strong foundation models and compute-heavy workloads will use provider APIs or cloud/GPU infrastructure. The architecture must avoid dependence on one model vendor and provide cost, timeout, retry, and fallback controls.

GPU rental is an implementation option, not a product requirement. It will be used only when measurement shows that local embedding, reranking, OCR, evaluation, or model adaptation benefits from it.

## 10. Relationship to the prototype

The previous RAG system may contribute carefully reviewed source data, ingestion utilities, or regression tests. Its chat-centered architecture and existing quality scores do not define this product and will not be migrated wholesale.

## 11. Decisions still requiring review

- The first eight to ten end-to-end use cases.
- Supported localities and how local administrative procedures are represented.
- Supported document types in the first release.
- Conditions that require professional review.
- User roles and access boundaries for the first operational release.
- Model-provider strategy and acceptable operating-cost envelope.
- Quantitative release thresholds for each evaluation dimension.
