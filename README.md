# Minh Long Legal Agent

An independently deployable Vietnamese legal decision-support service, initially focused on land law.

> **Project status:** Product Definition v1.0 is approved and an auditable local MVP is available for evaluation. It uses a deliberately small demo corpus and is not a production-ready legal adviser.

## Run the local MVP

Prerequisites: Python 3.11 or newer.

```powershell
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for the conversational Legal Agent or `http://127.0.0.1:8000/docs` for the API explorer.

### Enable real AI conversation

The application keeps the auditable case, facts, legal sources, and citations locally, while using Gemini or OpenAI for natural Vietnamese conversation. Without a server-side API key it deliberately stays in the limited rule-based fallback mode.

For a Gemini free-tier trial, create a key in [Google AI Studio](https://aistudio.google.com/apikey), then run:

```powershell
python scripts/configure_gemini.py
python -m uvicorn app.main:app --reload
```

Do not paste the key into chat, screenshots, frontend code, or Git. Gemini's free tier has usage limits, and Google states that free-tier content may be used to improve its products, so use synthetic test scenarios rather than confidential client documents.

To use OpenAI instead:

```powershell
python scripts/configure_ai.py
python -m uvicorn app.main:app --reload
```

The key is read only by the backend and must never be placed in `app/static`. Select the provider with `LEGAL_AGENT_PROVIDER=gemini` or `LEGAL_AGENT_PROVIDER=openai`. The trial defaults are `gemini-3-flash-preview` and `gpt-5.4`; preview model behavior and rate limits may change. OpenAI responses are requested with `store=false`; conversation history remains in the local Legal Agent database.

Run the tests with:

```powershell
python -m pytest
```

The default database is created at `data/legal_agent.db`. Set `LEGAL_AGENT_DB` to use another path.

Production-like environments require API-key authentication. Create keys per actor, tenant, and role:

```powershell
$env:LEGAL_AGENT_ENV="pilot"
python scripts/create_api_key.py --actor staff-001 --tenant minhlong --role case_staff
python scripts/create_api_key.py --actor reviewer-001 --tenant minhlong --role professional_reviewer
python -m uvicorn app.main:app
```

The console requests the key on the first protected API call. Development mode permits a local demo principal when no key is supplied; non-development mode requires `X-API-Key`.

For an isolated pilot deployment:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec legal-agent python scripts/create_api_key.py --actor staff-001 --tenant minhlong --role case_staff
docker compose exec legal-agent python scripts/bootstrap_source_packs.py
```

Pilot mode intentionally refuses the embedded demo corpus. A reviewed source pack must be imported before research can return a governed candidate provision. See the [Controlled Pilot Runbook](docs/operations/pilot-runbook.md).

The product is chat-first: the user describes a situation naturally, while the Agent creates and maintains the Legal Case invisibly, asks one material clarification at a time, resolves research context, researches governed sources, and returns a readable answer with expandable citations. Provenance, evidence maps, audit records, and professional review remain enforced behind the conversation.

## Vision

Minh Long Legal Agent is being built as a real legal case intelligence product rather than a question-answering RAG demonstration. It will help non-expert individuals, small businesses, Minh Long staff, and reviewing professionals analyze, understand, and prepare Vietnamese land-law matters.

The system will combine:

- natural Vietnamese conversation;
- structured Legal Case management;
- fact provenance and missing-fact detection;
- purposeful clarification;
- legal issue spotting;
- effective-date and locality-aware legal research;
- evidence-linked analysis and exact citations;
- risk and action-plan preparation;
- document intelligence;
- controlled generation of checklists and drafts;
- professional escalation and evaluation.

The Agent is a decision-support system. It does not replace a lawyer, notary, competent authority, or licensed professional.

## Product position

The Agent is developed first as an independent service with its own domain database, stable API, and minimal operational console. It is not being developed as a separate commercial website with its own marketplace, billing platform, or duplicated real-estate account system.

It will later integrate into the wider Minh Long ecosystem:

```text
Main Real Estate Platform                 AI Legal Agent Service
├── Users                                 ├── Legal Cases
├── Companies                             ├── Case Facts and Missing Facts
├── Properties and Listings               ├── Case Documents
├── Brokerage Requests                    ├── Legal Issues
├── Design / Construction Requests        ├── Research Sessions and Agent Runs
├── CRM                                   ├── Evidence and Citations
└── Payments                              ├── Risks and Action Plans
                                          ├── Generated Documents
                                          └── Evaluation and Safety Logs
```

The two systems will integrate through stable identifiers and justified snapshots. The Agent will not duplicate complete User, Company, or Property records from the main platform.

## Central unit of work: Legal Case

The central aggregate is a **Legal Case**, not a chat session.

A case may contain multiple conversations, facts, people, parcels, documents, issues, research runs, conclusions, action plans, and generated outputs. It can exist without a platform Property and can reference zero, one, or multiple Properties.

This is required for matters such as multi-parcel disputes, land recovery, inheritance before a property is onboarded, administrative complaints, deposit disputes, and situations supported only by uploaded documents.

## Evidence and provenance

Every material conclusion must be traceable through the following chain:

```text
Conclusion
→ Applicable facts
→ Legal rule
→ Source version
→ Exact citation location
```

Facts preserve their origin and confirmation history. The controlled provenance states are:

- `user_provided`;
- `document_extracted`;
- `staff_entered`;
- `agent_inferred`;
- `user_confirmed`;
- `professional_confirmed`.

An `agent_inferred` fact must never become confirmed automatically.

## Temporal and locality correctness

Vietnamese land-law outcomes may depend on jurisdiction, locality, relevant date, amendments, transitional rules, and provision-level validity. The system must therefore support:

- document and provision versioning;
- effective-date resolution;
- amendment, replacement, and supersession relationships;
- nationwide versus locality-specific rule separation;
- reproducible source snapshots;
- explicit applicability checks before synthesis.

Retrieved text is evidence for research, not automatic proof that a rule applies.

## Delivery roadmap

### Phase 1 — Agent Core

#### Phase 1A — Case Intelligence

- Legal Case model and lifecycle.
- Conversational intake.
- Structured facts with provenance.
- Missing-fact detection and clarification.
- Legal issue spotting.

#### Phase 1B — Legal Research

- Multi-document retrieval and research.
- Jurisdiction, locality, and relevant-date resolution.
- Source versioning and provision-level applicability checks.
- Evidence and citation-location mapping.

#### Phase 1C — Analysis and Action

- Evidence-linked analysis and synthesis.
- Risks, conditions, exceptions, and alternative interpretations.
- Executable action plans.
- Escalation and end-to-end evaluation.

### Phase 2 — Document Intelligence

- Supported document upload and classification.
- Structured extraction with provenance and uncertainty.
- Conflict detection across statements and documents.
- Document-to-fact and document-to-issue links.
- Case-specific document checklists.

### Phase 3 — Agent API

- Stable, versioned API contracts.
- Streaming.
- Service-to-service authentication and authorization.
- Audit logs, events or webhooks, and API documentation.

### Phase 4 — Main Real Estate Platform

- Users and organizations.
- Properties and listings.
- Brokerage and design/construction requests.
- CRM and administration.

### Phase 5 — Integration

- Create or link Legal Cases from business workflows.
- Reference platform records through IDs and controlled snapshots.
- Expose legal-check and case-preparation workflows through the Agent API.

## First-release non-goals

The first release will not support every field of law, every locality, or every document type. It will not automatically submit legal procedures, replace professional review, operate a lawyer marketplace, provide a native mobile app, value real estate, or provide a separate commercial billing system for the Agent.

Depth, correctness, auditability, and measurable usefulness take priority over broad feature coverage.

## Quality and release discipline

Progress is not measured by the number of modules implemented. A capability is complete only when evaluation demonstrates acceptable performance across its relevant dimensions, including:

- factual understanding and provenance;
- clarification and issue spotting;
- retrieval and source validity;
- temporal, jurisdiction, locality, and applicability correctness;
- completeness of conditions and exceptions;
- claim-to-evidence traceability;
- legal correctness and practical usefulness;
- uncertainty calibration and escalation;
- privacy, security, reliability, latency, and cost.

## Repository status

The repository contains the approved product definition, use-case blueprint, acceptance plan, TP.HCM scope, governed source packs, chat-first web application, API, SQLite persistence, authentication, evaluation, deployment packaging, and workflow tests.

```text
docs/
├── product/
│   └── product-definition.md
├── architecture/
│   └── system-boundary.md
└── decisions/
    ├── 0001-new-product-repository.md
    └── 0002-agent-service-boundary.md
```

Runtime code is organized under `app/`; tests are under `tests/`.

## Product governance

[Product Definition v1.0](docs/product/product-definition.md) is the approved source of truth for product identity, boundaries, primary users, unit of work, safety principles, and high-level delivery scope.

Implementation details may evolve through separate use-case, architecture, data, security, prompt, and evaluation specifications. A material change to the approved product definition requires a reviewed document version.

## Prototype relationship

The earlier `ai-legal-assistant` repository is retained as a land-law RAG prototype and research record. Data, utilities, or tests may be reused only after individual review. Its chat-centered architecture and development metrics do not define this product.

## Documentation

- [Product Definition v1.1](docs/product/product-definition.md)
- [Land-Law Corpus Standard](docs/product/land-law-corpus-standard.md)
- [Land-Law Corpus Packages](docs/product/land-law-corpus-packages.md)

Check governed corpus completeness by package with:

```powershell
python scripts/corpus_coverage.py
```
- [First-Release Decision Register](docs/product/first-release-decisions.md)
- [First-Release Locality Scope](docs/product/locality-scope.md)
- [Agent Core Use-Case Specification](docs/use-cases/README.md)
- [Use-Case Traceability and Acceptance Plan](docs/use-cases/traceability-and-acceptance.md)
- [System Boundary](docs/architecture/system-boundary.md)
- [MVP Architecture](docs/architecture/mvp-architecture.md)
- [Controlled Pilot Runbook](docs/operations/pilot-runbook.md)
- [Pilot Readiness Report](docs/evaluation/pilot-readiness-report.md)
- [ADR-0001: New Product Repository](docs/decisions/0001-new-product-repository.md)
- [ADR-0002: Agent Service Boundary](docs/decisions/0002-agent-service-boundary.md)
