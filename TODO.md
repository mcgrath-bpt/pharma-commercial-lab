# Maintained backlog

Updated **19 September 2026**. This is the authoritative working backlog for this lab. A completed local artefact does not imply deployment. Owners below describe the intended responsibility, not an assignment sent to another person.

Status vocabulary: **DONE_LOCAL**, **READY_FOR_ENVIRONMENT**, **OPEN**, **PARKED**. Evidence belongs alongside every completed item. Update this file when a task completes or its acceptance criterion changes; keep completed rows for traceability.

## Crawl · the next deployment slice

| ID | Priority | Status | Task / done when | Owner | Dependency / evidence |
|---|---|---|---|---|---|
| C01 | P0 | DONE_LOCAL | Recover and preserve all five business requests | Lab maintainer | `docs/SCENARIOS.md` |
| C02 | P0 | DONE_LOCAL | Define canonical entities, grains, keys, relationships and time rules | Lab maintainer | `contracts/canonical-model.json`, `docs/MODEL.md` |
| C03 | P0 | DONE_LOCAL | Hydrate one coherent synthetic world deterministically | Lab maintainer | 16 canonical CSVs, private manifest, repeatability test |
| C04 | P0 | DONE_LOCAL | Render distinct source IDs and usable, incomplete identity evidence | Lab maintainer | 15 source contracts; ambiguity test |
| C05 | P0 | DONE_LOCAL | Package S3 keys, counts, hashes, schema versions and completion markers | Lab maintainer | 19 manifested CSVs, two batches, validator |
| C06 | P0 | DONE_LOCAL | Supply original XLSX mapping and strict conversion path | Lab maintainer | 101 mappings; exact CSV equality; formula rejection |
| C07 | P0 | DONE_LOCAL | Define full expected rows, exceptions and DQ for S1–S5 at both cut-offs | Evaluator | 14 expected CSVs and independent oracle |
| C08 | P0 | DONE_LOCAL | Implement source-only local reference and hostile-data regression checks | Lab maintainer | `evidence/tests.txt`; 16 tests passed |
| C09 | P0 | DONE_LOCAL | Prepare stage-relative upload, raw loading and five-scenario Snowflake SQL | Lab maintainer | `src/upload_public.py`, `src/render_sql.py`, `sql/02_reference_gold.sql`; cloud execution open |
| C10 | P0 | OPEN | Bind exact existing stage, S3 URL, warehouse, named connection and isolated schema | Platform owner | Read stage definition; verify actual effective permissions |
| C11 | P0 | OPEN | Confirm or revise adopted business defaults | Business / architecture owner | UTC; current consent; correction window; active customers; current hierarchy; weekly campaign-to-date definition |
| C12 | P0 | READY_FOR_ENVIRONMENT | Upload only the public tree and verify stage visibility | Platform owner | C10; upload result, SHA checks and LIST evidence |
| C13 | P0 | READY_FOR_ENVIRONMENT | Run S2 and S4 through S3 → existing stage → Snowflake | Lab maintainer | C12; zero row differences at both checkpoints; query IDs saved |
| C14 | P0 | READY_FOR_ENVIRONMENT | Run S3 through the XLSX adapter and real stage loading | Lab maintainer | C13; correct realignment, missing flag and forced tie failure |
| C15 | P0 | OPEN | Demonstrate identical replay and recovery from a failed cloud batch | Lab maintainer | C13; no duplicate output, incomplete batch invisible, repaired rerun succeeds |
| C16 | P0 | OPEN | Enforce evaluator/builder access separation | Platform owner | Builder cannot read truth, generator inputs or expected rows via S3, stage, role inheritance or local workspace |
| C17 | P0 | OPEN | Record a release in Git and bind it to immutable data and contract fingerprints | Lab maintainer | Real commit SHA, manifest fingerprint and cloud execution evidence; no fabricated SHA |
| C18 | P0 | OPEN | Demonstrate first two scenarios and capture acceptance | Business / architecture owner | C13, C15–C17 complete; observed results and agreed remaining limitations |

## Walk · add operational proof and reuse

| ID | Priority | Status | Task / done when | Dependency |
|---|---|---|---|---|
| W01 | P1 | READY_FOR_ENVIRONMENT | Run S1 and S5 in Snowflake and reconcile every row and exception | C13, C16 |
| W02 | P1 | OPEN | Schedule S2 by 06:30 and S1 by 07:00 UTC; detect absent/stale source deliveries | C11, C13, W01; measured run and publication timestamps |
| W03 | P1 | OPEN | Schedule weekly S5; agree the weekly deadline and report cut-off | C11, W01 |
| W04 | P1 | OPEN | Deliver and verify notifications for threshold breaches plus S3/S4 exceptions | W02; notification evidence, no silent empty-data pass |
| W05 | P1 | OPEN | Add physical malformed-file, removed-column, added-column and type-drift profiles | File/header mutations exist; full delivery profiles still needed |
| W06 | P1 | OPEN | Add delayed consent/provider updates and reports before/after visibility | C07; no future knowledge in earlier outputs |
| W07 | P1 | OPEN | Add genuine ambiguity, source identity merges/splits and identifier reuse | C04; no name-based guessed matches |
| W08 | P1 | OPEN | Test stale higher-arrival/lower-version files and higher-version rejected corrections in cloud | C15; last trusted state retained |
| W09 | P1 | OPEN | Validate source master natural keys and time-overlap rules beyond current fixture | C08; explicit reject/quarantine policy per reference entity |
| W10 | P1 | OPEN | Add manifest authentication and concurrent loader coordination if required | Single trusted uploader/loader currently assumed |
| W11 | P1 | OPEN | Introduce a minimal business-contract validator and compiler | Reviewed hand implementation and acceptance contracts are the target |
| W12 | P1 | OPEN | Compare generated SQL to the same private truth without exposing the oracle | W11, C16 |
| W13 | P1 | OPEN | Add persistent incremental processing and prove equivalence to full recomputation | C15; don't optimise away correctness |
| W14 | P1 | OPEN | Add Git-based release evidence and deployment reconciliation | C17, W11; NOOP vs safe derived-asset rebuild |
| W15 | P1 | OPEN | Scale only after profiling generator/oracle and warehouse cost | The shipped fixture is for semantic coverage, not load testing |

## Run · explicitly parked

| ID | Status | Capability | Re-entry condition |
|---|---|---|---|
| R01 | PARKED | Production role provisioning, CI/CD promotion and recovery automation | Cloud acceptance is reliable |
| R02 | PARKED | General bitemporal MDM, broad event-sourcing and universal source contracts | A concrete scenario needs them |
| R03 | PARKED | Governance/catalogue/ITSM integrations | They unblock a measured acceptance requirement |
| R04 | PARKED | Arbitrary code generation and unrestricted SQL deployment | Approved implementation patterns and lifecycle controls exist |
| R05 | PARKED | Large prescription volumes, real market calibration and causal attribution | A new agreed business question requires them |
| R06 | PARKED | Patient-level data | Outside this commercial pilot's current scope |

## Decision and change log

- **19 September 2026:** all five acceptance contracts recovered; a 100-HCP Crawl fixture adopted before scale. Public product codes are shared reference codes, public customer matching is exact-token only.
- **19 September 2026:** local reference and independent oracle agree at two reporting cut-offs. Replay testing found and fixed duplicate campaign diagnostics. Workbook conversion is byte-identical to staged CSV.
- **19 September 2026:** S3 upload and Snowflake/SLA/notification checks remain open. No infrastructure, external messages, tasks or recurring automations were created.

**Next concrete action:** bind the existing stage and run C12–C13, starting with S2 and S4. S1 and S5 already have acceptance data; they do not need a second modelling exercise.
