# ADR-0001: Build the production agent in a new repository

**Status:** Accepted
**Date:** 2026-07-14

## Context

The earlier `ai-legal-assistant` repository validated parts of a land-law retrieval pipeline but remained a chat-centered RAG prototype. Continuing directly from that structure would make prototype assumptions appear to be production decisions.

## Decision

Create `minhlong-legal-agent` as a new product repository. Begin with reviewed product, use-case, architecture, prompt, safety, and evaluation specifications before production implementation.

Retain the prototype repository separately. Reuse is allowed only at the level of individually reviewed data, utilities, tests, or findings.

## Consequences

- The Git history communicates intentional product development rather than a cosmetic V2 rewrite.
- The Legal Case becomes the central unit of work.
- Existing prototype code receives no implicit compatibility guarantee.
- Initial progress may appear slower because acceptance criteria and evaluation are designed before feature implementation.
- Integration with the future Minh Long website remains an explicit architectural requirement without allowing the preliminary website blueprint to limit the agent.
