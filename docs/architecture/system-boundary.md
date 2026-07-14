# System Boundary

**Status:** Accepted baseline

## 1. Architectural principle

Minh Long Legal Agent is a domain service for legal-case intelligence. It owns legal processing state and exposes capabilities through an API. It is not merely a stateless collection of model endpoints, and it is not the future real-estate platform.

## 2. Ownership boundaries

### Main Real Estate Platform owns

- users and organizations;
- properties and listings;
- brokerage requests;
- design and construction requests;
- CRM and commercial workflows;
- payments.

### AI Legal Agent owns

- legal cases and case lifecycle;
- case facts and missing facts;
- case documents and extraction results;
- legal issues;
- research sessions;
- agent runs and tool traces;
- evidence and citations;
- risk assessments and action plans;
- generated legal-support outputs;
- evaluation and safety logs.

Legal-source content and provision-level validity belong inside the Legal Agent boundary or a dedicated legal-knowledge service governed by the Agent product. The implementation choice will be resolved during knowledge architecture design.

## 3. Integration references

A Legal Case can carry optional external references:

```json
{
  "tenant_id": "company_001",
  "user_id": "user_001",
  "property_ids": ["property_015"],
  "business_request_ids": ["brokerage_request_020"],
  "legal_case_id": "case_103"
}
```

Rules:

- `legal_case_id` identifies the Agent-owned aggregate.
- A case may link to zero, one, or multiple properties.
- A property is never required to create a case.
- External IDs do not transfer data ownership to the Agent.
- The Agent stores only snapshots needed to explain or reproduce a legal analysis.
- Every snapshot records source, capture time, external version when available, and purpose.
- Integration must tolerate an external record becoming unavailable without corrupting the legal case history.

## 4. Why cases must be independent

Many valid matters do not correspond to a single platform property, including multi-parcel disputes, land recovery, inheritance before property onboarding, administrative complaints, deposit disputes, and matters supported only by uploaded documents.

The core invariant is therefore:

```text
Legal Case exists independently
    ├── references 0..n external Properties
    ├── references 0..1 external User
    ├── references 0..1 external Tenant or Organization
    └── references 0..n external Business Requests
```

Cardinalities describe initial integration intent and may be expanded without changing case ownership.

## 5. Minimal internal console

The Agent needs a minimal interface during development and controlled operation:

```text
Legal Agent Console
├── Case list and case creation
├── Chat and case intake
├── Facts and missing facts
├── Documents and extraction review
├── Legal issues
├── Evidence and citations
├── Risks and action plan
├── Generated outputs
└── Agent-run and evaluation inspection
```

This console is not a marketing website, marketplace, payment application, or final customer portal. Its purpose is to make Agent behavior observable, testable, and reviewable.

## 6. Current focus

Development remains focused on the AI Legal Agent Core. The real-estate platform is represented only through explicit integration contracts and identifiers until the Agent Core reaches its agreed quality gates.
