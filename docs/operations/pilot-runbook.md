# Controlled Pilot Runbook

**Status:** Baseline  
**Date:** 2026-07-14

## Safety position

Pilot mode is not authorized for real legal reliance until a reviewed source pack, named locality, qualified reviewer, retention policy, incident owner, and evaluation thresholds are approved. The application fails closed on absent governed sources and requires API keys outside development.

## Start

1. Copy `.env.example` to `.env` and keep demo sources disabled.
2. Build and start with `docker compose up --build -d`. Compose imports the included governed source packs idempotently before starting the API.
3. Verify `/health` reports `environment: pilot`, `auth_required: true`, and `legal_coverage: governed_only`.
4. Create staff and reviewer keys inside the configured environment using `scripts/create_api_key.py`.
5. Import only a reviewed source pack using `scripts/import_source_pack.py`.
6. Execute the full regression suite and an approved professional scenario set before admitting cases.

## Source-pack gate

An imported document requires identity, number, issuing authority, HTTPS official URL, SHA-256 content hash, effective interval, controlled lifecycle status, jurisdiction, version, and provision-level text/location. Importing a source does not itself constitute legal approval; the source pack must be independently reviewed.

## Backup and recovery

- Stop case writes or take a consistent database snapshot before backup.
- Back up the SQLite database volume and the exact imported source-pack files.
- Test restoration into an isolated environment.
- Verify case, artifact, audit, API-key, source, and schema-migration counts.
- Rotate API keys if their confidentiality may have been affected.

SQLite is the controlled-pilot store. Move to a managed transactional database before concurrency, availability, or organizational scale exceeds the approved pilot envelope.

## Incident response

Immediately suspend affected keys and stop output release for suspected cross-tenant disclosure, incorrect applicable-law selection, fabricated authority, bypassed review gate, or unauthorized action. Preserve audit and source snapshots, identify affected cases/artifact versions, notify the assigned incident owner, and add a regression case before reopening.

## Release checklist

- Tests and `diff --check` pass.
- No demo-source fallback in pilot.
- Authentication is required and keys follow least privilege.
- Named source/locality coverage is reviewed.
- Mandatory review triggers are configured and exercised.
- Backup restoration is tested.
- S0/S1 evaluation failures are zero.
- A qualified owner signs the release record.
