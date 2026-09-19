# Synthetic pharma commercial lab · v0.1.0

This is a working local acceptance pack for five pharma commercial pipeline scenarios. It contains a canonical synthetic world, imperfect Veeva CRM-like, IQVIA-like and Salesforce-like projections, upload-ready CSV deliveries, an XLSX territory fixture, manifests, Snowflake loading SQL and independent expected results.

**Local implementation and tests are complete. S3 upload, Snowflake execution, access separation and timed delivery have not been exercised.** An existing external stage is assumed throughout. No stage, bucket, credentials, roles or warehouse are created by the pack.

Start with [the design and its trade-offs](docs/DESIGN.md), [the five acceptance contracts](docs/SCENARIOS.md) and [the maintained backlog](TODO.md). Deployment steps are in [the runbook](docs/RUNBOOK.md).

## What is in the pack

| Artefact | Location | Purpose |
|---|---|---|
| Canonical model and DDL | `contracts/canonical-model.json`, `sql/00_canonical_private.sql` | 16 entities with keys, types, relationships, grains and time semantics |
| Hydrated canonical records | `data/private_evaluator/canonical/` | Evaluator-only CSVs for every entity |
| Reproducible inputs | `config/crawl.json` | Seed, population, delivery schedule and deliberate defects |
| Generator | `src/generate.py` | Creates one world and projects it into the three source dialects |
| Source contracts and mappings | `contracts/source-projections.json`, `docs/MODEL.md` | Source fields, keys, authority and mapping rules |
| S3-ready tree | `data/public_s3/` | The **only** directory the uploader accepts |
| Delivery manifests | `data/public_s3/synthetic/pharma/pharma-lab-0.1.0/control/` | Exact keys, columns, counts, byte lengths and SHA-256 fingerprints |
| XLSX fixture | `data/public_s3/synthetic/pharma/pharma-lab-0.1.0/business_files/territory/` | Monthly mapping input, with an executable converter |
| Expected results | `data/private_evaluator/expected/b001/` and `b002/` | Five scenario tables, exceptions and DQ results at both cut-offs |
| Reference implementation | `src/reference.py` | Reads public source files only |
| Oracle | `src/oracle.py` | Reads canonical records and explicit projection decisions only |
| Snowflake hand implementation | `sql/02_reference_gold.sql` | All five scenarios, supplied for cloud verification |
| Exact-file loaders | `src/render_sql.py`, `sql/generated/` | Load through the existing stage; publish batch visibility after count checks |
| Test evidence | `evidence/validation-report.json`, `evidence/tests.txt` | Results of executed local checks, including negative cases |

## Quick local check

From this directory, with Python 3.10 or later:

```sh
python3 src/run_local.py
```

The Python workflow uses the standard library. It validates the deliveries, calculates results from the public sources, calculates the oracle independently, compares full row multisets and runs regression checks. Missing, extra, duplicate and changed rows are failures.

To regenerate the core CSV/JSON fixture, use a new empty destination:

```sh
python3 src/generate.py --config config/crawl.json --out /tmp/pharma-replay
python3 src/run_local.py --data /tmp/pharma-replay
```

Core CSV/JSON output is byte-reproducible for the same input and implementation. The supplied XLSX is an additional static business-file fixture; the generator does not author Excel workbooks. Run its adapter and compare the resulting CSV to the generated territory CSV. XLSX ZIP/container bytes are not part of the generator determinism claim.

## Population and replay

The crawl world has 100 HCPs, 12 HCOs, four products, four territories, eight representatives and four campaigns. It covers 1 July–13 September 2026, then two deliveries on 14 and 15 September. There are 300 initial interactions, a duplicate delivery row, four new interaction versions and two corrections/tombstones. Weekly commercial observations are included as a supporting feed, with one restatement. They are not needed to claim success for any of the five scenarios.

All people, products, organisations, identifiers and measures are invented. `ZZ` is a synthetic market marker. No patient records, real contact details or proprietary vendor schemas are included.

## Crawl, walk, run

**Crawl:** prove S2 and S4 through the real S3/stage/Snowflake path. Compare every result to the supplied truth sets. Then run S3 through the real XLSX adapter. All five already have local contracts and reference results, but this is not evidence of five deployed pipelines.

**Walk:** add S1 and S5 to the cloud demonstration, deadlines and notifications, identity ambiguity profiles, late consent/reference delivery and schema/file fault profiles. Make the pipeline contracts generate the reviewed SQL.

**Run:** increase volume after measuring execution cost, add stateful orchestration, broader source evolution, real permissions, CI/release reconciliation and operational recovery.

The immediate design challenge is to prove correct versioning, joins and exception handling. More synthetic rows will not compensate for weak acceptance rules.
