# Minh Long Legal Agent

Production-oriented Vietnamese legal case intelligence platform, initially focused on land law.

> Status: Product discovery and architecture. This repository is not a demo chatbot and is not yet ready for legal use.

## Product direction

Minh Long Legal Agent is designed to help users describe a legal situation, build a structured case file, identify missing facts and legal issues, research applicable law, explain possible paths, prepare documents, and escalate matters for professional review.

The product will operate independently through its own API and user experience, while remaining ready for integration into the Minh Long company website.

The agent owns its legal-case data and processing state. It may reference users, organizations, properties, or business requests from a future real-estate platform, but it does not duplicate ownership of those platform records.

## Current phase

No production implementation will begin until the following artifacts are reviewed:

1. Product definition and scope.
2. Eight to ten real land-law use cases.
3. Legal Case data model and agent workflow.
4. Legal-source and citation architecture.
5. Prompt, safety, and evaluation specifications.

## Repository history

The earlier `ai-legal-assistant` repository is a land-law RAG prototype. It is retained as research evidence and a source of selectively reusable tests or data, not as the architecture of this product.

## Documentation

- [Product definition](docs/product/product-definition.md)
- [System boundary](docs/architecture/system-boundary.md)
- [Architecture decision: new product repository](docs/decisions/0001-new-product-repository.md)
- [Architecture decision: agent service boundary](docs/decisions/0002-agent-service-boundary.md)
