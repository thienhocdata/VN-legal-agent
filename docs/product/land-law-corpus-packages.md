# Land-Law Corpus Packages

**Version:** 1.0

**Status:** Approved

**Approved:** 2026-07-14

**Machine registry:** `corpus/land/package-registry.json`

## Operating rule

The land-law domain is delivered through ten business packages. A package is enabled only after its complete national, historical, cross-domain, and locality source inventory passes the Land-Law Corpus Standard. A model's background knowledge never counts as package coverage.

Priorities control ingestion order, not legal importance:

- `P0`: first usable transaction and certificate product;
- `P1`: parcel, planning, land-use purpose, and financial depth;
- `P2`: high-risk recovery and dispute preparation requiring early professional review.

## Package map

| ID | Package | Priority | Initial product outcome |
|---|---|---:|---|
| `certificate` | Giấy chứng nhận | P0 | Registration, first issue, exchange, reissue, correction, change registration, attached assets |
| `transactions` | Giao dịch | P0 | Transfer, gift, inheritance, capital contribution, deposit, notarization, mortgage-aware registration |
| `parcel` | Thửa đất | P1 | Split, merge, minimum dimensions, boundaries, access, cadastral and infrastructure conditions |
| `legal-status` | Tình trạng pháp lý | P0 | Pre-purchase checks for dispute, enforcement, mortgage, restriction, recovery, violation and transfer eligibility |
| `planning` | Quy hoạch | P1 | Land-use and construction planning, road lines, projects, recovery plans and preliminary buildability |
| `land-use-purpose` | Mục đích sử dụng đất | P1 | Land classification, permission/registration requirements, conversion grounds and financial consequences |
| `state-recovery` | Nhà nước thu hồi | P2 | Recovery, inventory, compensation, support, resettlement, coercion, complaint and handover |
| `finance` | Tài chính | P1 | Identify taxes, fees, land-use/lease obligations, inputs, formulas and official verification points |
| `hcm-procedures` | Thủ tục TP.HCM | P0 | Versioned registry of dossiers, forms, receiving offices, processing steps, time, fees and results |
| `dispute-triage` | Tranh chấp sơ bộ | P2 | Classify dispute paths, evidence, authority, time limits, urgent measures and professional escalation |

## 1. Giấy chứng nhận (`certificate`)

Coverage includes first land registration and certificate issuance, exchange, lost-certificate reissue, correction, confirmation of changes, change registration, assets attached to land, no-paper cases, competence, forms, and cadastral data.

The complete source inventory starts with the 2013 regime and Law 35/2018/QH14 for historical comparison; Laws 31/2024/QH15 and 43/2024/QH15; Decrees 101/2024/ND-CP and 102/2024/ND-CP; all current circulars governing cadastral dossiers, certificates, forms, and land data; Circular 09/2024/TT-BTNMT when certificate data is processed; and every effective TP.HCM publication, internal procedure, amendment, replacement, dossier, time, fee, and receiving-office instrument. Decision 651/QD-UBND dated 2025-02-18 is a verified source lead but remains subject to later-change resolution.

## 2. Giao dịch (`transactions`)

Coverage includes transfer, gift, inheritance, capital contribution, deposit, invalid contracts, notarization/authentication, post-transaction registration, marital property, representatives, minors, and mortgaged property.

The inventory includes the complete applicable land-law instruments; Civil Code rules governing transactions, contracts, inheritance, joint property, mortgage, usufruct and neighboring-property rights; the Notarization Law 46/2024/QH15 and its instruments; marriage and family, real-estate business, housing, credit-institution, and security-registration instruments; and complete TP.HCM change-registration procedures. Decree 49/2026/ND-CP and Resolution 254/2025/QH15 are versioned dependencies where their mechanisms affect a transaction.

## 3. Thửa đất (`parcel`)

Coverage includes split, merge, minimum area and dimensions, common access, passage rights, boundaries, markers, mixed-use parcels, planning constraints, infrastructure, cadastral surveying and records.

National sources include complete land-law, registration, implementation, civil neighboring-property, surveying, cadastral-map, and cadastral-record instruments. TP.HCM coverage requires the currently effective split/merge decision, every amendment/replacement, procedures, land-type and locality distinctions, and linked planning/infrastructure rules. An old local split rule may never be reused without current-effect verification.

## 4. Tình trạng pháp lý (`legal-status`)

Coverage includes disputes, enforcement attachment, mortgage, transaction restrictions, recovery, unresolved violations, registered security, prevention notices and transfer eligibility.

Sources span land law, civil law, civil procedure, civil judgment enforcement, notarization, credit institutions, security registration, land-information access, administrative sanctions, and TP.HCM information-request procedures. Decree 281/2026/ND-CP is recorded as issued on 2026-07-13 but not effective until 2026-08-31; it must not be applied before that date.

This package also maintains a non-legislative due-diligence checklist and clearly distinguishes information the user must verify with the land registry, enforcement authority, notarial organization, bank, planning source, or dispute file.

## 5. Quy hoạch (`planning`)

Coverage includes land-use planning and annual plans, construction and urban/rural planning, road boundaries, density, floor-area ratio, project/recovery status, and preliminary buildability.

Sources include the applicable land, planning, urban/rural planning, construction, technical-regulation, TP.HCM master/local planning, annual land-use plan, and building-permit instruments. Legal documents and geospatial/planning artifacts are stored in separate linked layers; maps are not embedded as ordinary legal text.

## 6. Mục đích sử dụng đất (`land-use-purpose`)

Coverage includes residential, agricultural, rice, commercial/service, production, mixed-use classifications; permission versus registration; decision grounds; planning dependencies; and financial obligations.

Sources include complete Land Law, Decrees 102/2024, 103/2024, 71/2024 and 291/2025, rice-land instruments, planning/land-use plans, TP.HCM limits, price tables, factors, conversion procedures, and competence delegations. Amendment relationships are mandatory.

## 7. Nhà nước thu hồi (`state-recovery`)

Coverage includes recovery grounds and notice, survey, measurement, inventory, coercive inventory, compensation plans, compensation price, support, resettlement, complaints, handover and non-compensable cases.

Sources include complete land law; Decrees 88/2024, 71/2024 and 102/2024; Resolution 254/2025/QH15 and implementing Decrees 49/2026 and 50/2026 where applicable; complaints, administrative procedure and state-compensation rules; and every effective TP.HCM compensation, support, resettlement, minimum-resettlement, livelihood, vocational-conversion, specific-price and plan-approval instrument.

## 8. Tài chính (`finance`)

Coverage includes personal income tax, registration fee, appraisal and certificate fees, land-use and land-rent obligations, conversion obligations, exemptions, reductions, inputs, formulas and verification points.

Sources include Decrees 103/2024, 291/2025, 71/2024 and 50/2026 where applicable; personal-income-tax, registration-fee, fee/charge and Ministry of Finance instruments; TP.HCM fee resolutions, land price tables, adjustment decisions, factors and financial-obligation procedures. Amendment sources are never treated as independent parallel rules.

V1 identifies the obligation, inputs, legal formula and official verification route. It does not assert a final payable amount when authoritative case data is incomplete.

## 9. Thủ tục TP.HCM (`hcm-procedures`)

This is a versioned procedure registry, not a single document. Each procedure stores name, code, legal basis, applicant, conditions, dossier composition and quantity, receiving/resolving authority, submission channel, sequence, time, fee, result, forms, effective interval, publication decision, and amendment/replacement chain.

The initial inventory includes first registration/certificate, transfer, gift, inheritance, capital contribution, exchange, lost-certificate reissue, correction, split, merge, conversion, attached-asset registration, mortgage release, land-data access, residential-area redetermination, recovery/compensation publications and land-finance procedures. Sources are the TP.HCM procedure portal, publication decisions, internal processes, amendments/repeals, public-service records, and verified operational receiving authorities.

## 10. Tranh chấp sơ bộ (`dispute-triage`)

Coverage includes land-use entitlement, boundary/access, contract, inheritance, marital property, administrative decision, recovery/compensation disputes, conciliation and authority routes, limitation periods, urgent measures and mandatory professional escalation.

Sources include complete land, civil, civil procedure, administrative procedure, complaints, grassroots conciliation, civil enforcement, notarization and marriage/family instruments; Judicial Council guidance; officially published precedents and selected judgments for land rights, contracts, deposits, inheritance, access, household land, informal transactions and recognition of land-use rights; commune-level land-dispute conciliation and TP.HCM complaint procedures.

The package prepares and triages. It does not replace litigation strategy or professional representation.

## Activation gate shared by all packages

A package remains disabled when any mandatory document is missing, partial, unverified, temporally unresolved, or locally unresolved. Activation additionally requires complete source-family inventory, full-text verification, provision-level retrieval tests, date/locality boundary tests, contradiction tests, and zero fabricated citations in the approved package evaluation set.
