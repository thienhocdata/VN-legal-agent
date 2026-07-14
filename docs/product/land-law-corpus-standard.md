# Land-Law Corpus Standard

**Version:** 1.0

**Status:** Approved

**Approved:** 2026-07-14

**Domain:** Vietnamese land law

## 1. Binding product decision

Minh Long Legal Agent develops one complete legal domain at a time. The first domain is Vietnamese land law. The product must not claim a land-law topic is supported merely because a model can discuss it or because a few selected provisions have been imported.

Within this domain, the corpus is built from complete official documents and their historical versions. Retrieval chunks, summaries, embeddings, and model answers are derived views; none may replace the preserved full text.

## 2. Domain boundary

The land-law corpus includes:

- every Vietnamese Land Law and amendment required to resolve matters across supported historical periods;
- implementing decrees, resolutions, decisions, circulars, consolidated texts, transitional rules, and authoritative corrigenda;
- locality-specific instruments for each locality explicitly enabled by the product;
- complete instruments from adjacent fields when they materially govern a land-law conclusion, including civil transactions, inheritance, marital property, housing, real-estate business, construction, planning, notarization, registration of security interests, taxation, fees, enforcement, complaints, and procedure;
- official guidance, precedents, and judgments only as separately classified authority, never silently treated as legislation.

The Agent uses adjacent-field sources only to answer a land-law matter. Their presence does not enable a general civil, tax, family, criminal, or litigation-advice product.

## 3. Historical coverage

The target historical spine is the Land Laws of 1987, 1993, 2003, 2013, and 2024, together with amendments, replacements, implementing instruments, and transitional provisions applicable to each period.

The first executable comparison milestone is 2013-2024. Earlier regimes follow after the same completeness gate passes for that milestone.

## 4. Source-of-truth requirements

Every accepted document version must preserve:

1. an official source URL and issuing authority;
2. the original downloaded artifact or an official full-text snapshot;
3. a SHA-256 digest of every preserved artifact and extracted full text;
4. document identity, type, number, issue date, publication date, and jurisdiction;
5. effective-from and effective-to dates, legal status, and known special effective dates;
6. the complete extracted text;
7. structural units down to chapter, section, article, clause, and point when present;
8. stable source offsets or page locations from each structural unit to the original artifact;
9. amendment, replacement, repeal, consolidation, guidance, and implementation relationships;
10. extraction method, verification state, verifier, and verification time.

## 5. Completeness gate

A document may be marked `full_text_verified` only when all of the following pass:

- all official artifact parts are present and their hashes match the manifest;
- the extracted text is non-empty and preserves the document from title through signature or closing provision;
- expected and parsed article counts match when the document is article-structured;
- provision identifiers and order are unique and continuous, with every omission explicitly explained;
- a sample of first, middle, and final pages has been visually checked against the PDF;
- legal metadata and effective dates have been independently checked;
- relationships that affect current applicability have been recorded;
- automated integrity tests pass.

`excerpt`, `summary_only`, `partial`, and `unverified` records may support development diagnostics but must never satisfy production coverage or support a definitive legal claim.

## 6. Answering rules

For every legal conclusion the system must resolve the relevant date, jurisdiction, locality, subject, and transaction before selecting sources.

The model is a synthesis engine, not a source of law. If the governed corpus lacks a material rule, version, amendment relationship, or local instrument, the Agent must disclose the corpus gap and limit or escalate the answer. It must not fill the gap from model memory.

Every material conclusion must trace through:

```text
conclusion
-> applicable case facts
-> exact provision
-> document version
-> effective interval and locality
-> preserved official artifact
```

## 7. Delivery sequence

The domain is organized into the ten approved business packages in [Land-Law Corpus Packages](land-law-corpus-packages.md). Package priority controls delivery order while the completeness gate remains identical.

1. Corpus schema, full-text importer, integrity checks, and coverage reporting.
2. Complete Land Law 2013 and Land Law 2024 source artifacts and structural text.
3. Amendment and transition mapping between the 2013 and 2024 regimes.
4. Complete national implementing instruments for those regimes.
5. Complete current and historical TP.HCM land-law instruments.
6. Land Laws 2003, 1993, and 1987 with their applicable instrument networks.
7. One independently gated locality pack at a time beyond TP.HCM.

Chat features do not take priority over corpus completeness, temporal correctness, and claim-to-source traceability.

## 8. Release evidence

Coverage is measured by authoritative source inventories and provision-level integrity, not by document count alone. Each enabled topic requires:

- a reviewed source inventory with no unexplained mandatory-source gaps;
- 100% full-text and required-metadata coverage for inventory items;
- provision-level effective-date and locality checks;
- comparison tests across relevant historical regimes;
- positive, negative, boundary, conflict, and corpus-gap scenarios;
- zero invented citations in the release evaluation set.

The four initial source packs are retained as demo and migration fixtures. They do not constitute a complete land-law corpus.
