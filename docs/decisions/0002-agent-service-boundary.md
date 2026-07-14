# ADR-0002: Give the Legal Agent an independent domain boundary

**Status:** Accepted

**Date:** 2026-07-14

## Context

The Legal Agent must eventually integrate into a wider real-estate service platform. Treating it as stateless endpoints would lose legal-case state, evidence lineage, research history, and evaluation data. Treating it as the owner of users and properties would duplicate the main platform and create conflicting systems of record.

Legal matters also exist without a platform property and can involve multiple parcels, documents, people, or administrative actions.

## Decision

The Legal Agent will be an independently deployable domain service with its own operational database and a minimal internal console.

It owns Legal Case aggregates and legal-processing records. It references external platform entities by ID and stores only snapshots required for reproducibility or legal analysis.

A Legal Case can exist without a Property and may reference zero to many Properties.

## Consequences

- Agent development and testing can proceed before the real-estate platform exists.
- Legal state has a clear system of record.
- The future platform can initiate or link cases without owning their internal processing state.
- Integration requires stable IDs, authentication, authorization, versioned contracts, and lifecycle policies.
- Snapshot storage must be explicit and auditable.
- A small internal console is required, but commercial website features remain out of scope for the current phases.
