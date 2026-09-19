# Hydration and deployment runbook

## 1. Verify the local pack

Run from the extracted lab directory:

```sh
python3 src/run_local.py
```

Inspect `evidence/validation-report.json`. All five scenario outputs, exception sets and percentage DQ results must match at b001 and b002. `ALERT` inside a DQ result can be expected; a failed reconciliation is not.

Run the spreadsheet adapter independently:

```sh
python3 src/xlsx_to_csv.py \
  data/public_s3/synthetic/pharma/pharma-lab-0.1.0/business_files/territory/territory_mapping_202609.xlsx \
  /tmp/territory_mapping.csv
```

The output must be byte-identical to `sources/manual/territory_mapping/batch=b001/part-00001.csv` beneath that release root. The `.receipt.json` records workbook and CSV hashes. This adapter accepts only the named sheet, exact columns and typed/ISO dates. It rejects formulas and merged cells. For a changed business workbook, create a new delivery, regenerate its manifest and update the acceptance results; do not overwrite b001.

## 2. Bind the existing stage to the local layout

Obtain the exact existing stage name, its URL and the intended isolated target schema. They are deliberately not guessed. Illustrative values in generated SQL are **placeholders**:

```text
stage object:      LAB_DB.INGEST.EXISTING_S3_STAGE
stage URL:         s3://YOUR_BUCKET/EXISTING_STAGE_PREFIX/
target schema:     LAB_DB.PHARMA_CRAWL
```

Read the stage definition and LIST permission using the deployment role. Confirm the URL root matches the `--stage-url` supplied to the uploader. Our `synthetic/pharma/...` keys are relative to that URL root. Do not add the existing prefix twice. SQL rendering supports unquoted three-part stage and two-part schema identifiers; unusual quoted names need an explicit renderer change.

The role needs usage on the relevant database, schema, warehouse and existing stage; permission to create the isolated derived schema/objects; and its intended DML privileges. Configure a named Snowflake connection using your existing authentication method. No passwords or private keys belong in this pack. Confirm the runtime role cannot read evaluator truth.

## 3. Preview and upload the public tree

The uploader requires AWS CLI v2 supporting conditional `put-object` and access to the stage's existing S3 prefix. Bucket encryption defaults are used. Follow your existing KMS policy; the script does not change it.

```sh
python3 src/upload_public.py \
  --public-root data/public_s3 \
  --stage-url s3://YOUR_BUCKET/EXISTING_STAGE_PREFIX/
```

This prints the plan without contacting AWS. Execute the same command with `--execute` when the destination is correct. It sends only the public tree: data and contracts first, manifests second, ready markers last. Different existing bytes fail. An identical existing object can be resumed only when its remote SHA-256 is readable and matches. No recursive upload of the pack root is appropriate: that would expose truth and expected answers.

S3 SHA-256 checksums are not ETags. Existing objects created without a readable SHA-256 cannot be assumed identical. Use a new release prefix or investigate explicitly. A 409 conditional-write conflict should be retried by rerunning after inspecting the conflict; the uploader does not loop indefinitely.

## 4. Render and run Snowflake hydration

```sh
python3 src/render_sql.py \
  --public-root data/public_s3 \
  --stage YOUR_DB.YOUR_SCHEMA.YOUR_EXISTING_STAGE \
  --schema YOUR_DB.YOUR_ISOLATED_LAB_SCHEMA \
  --out /tmp/pharma-sql
```

Review `01_load_b001.sql` and `01_load_b002.sql`. They create raw/audit objects in the named schema, load exact file lists, assert counts and expose only complete batches. They do not create or replace the stage. Run b001 before b002, stop on any SQL error, and retain query IDs/COPY results. Raw failed loads remain for diagnosis; a failed batch must not be promoted manually. Re-running identical loads is permitted. Rebuilds after expired COPY metadata or partial manual changes need a new isolated schema; do not enable `FORCE=TRUE` casually.

For the provided hand-built baseline, the optional Python harness keeps one Snowflake session, because its derived tables are temporary. Install/configure the official `snowflake-connector-python` in your environment, then:

```sh
python3 src/run_snowflake.py \
  --public-root data/public_s3 \
  --connection YOUR_NAMED_CONNECTION \
  --stage YOUR_DB.YOUR_SCHEMA.YOUR_EXISTING_STAGE \
  --schema YOUR_DB.YOUR_ISOLATED_LAB_SCHEMA \
  --out /tmp/pharma-cloud-evidence
```

This runs b001, calculates/exports the 14 September checkpoint, then b002 and the 15 September checkpoint. It exports lower-case headers and normalised numeric/boolean representations, and writes execution/query-ID evidence. The reference SQL and cloud harness have **not been executed against Snowflake** in this delivery. An account-level check is the next open gate.

Compare each export from the evaluator workspace:

```sh
python3 src/validate.py \
  --expected data/private_evaluator/expected/b001 \
  --actual /tmp/pharma-cloud-evidence/b001
python3 src/validate.py \
  --expected data/private_evaluator/expected/b002 \
  --actual /tmp/pharma-cloud-evidence/b002
```

Use these same CSV contracts to evaluate agent-generated pipelines. The baseline reference is a correctness target, not proof that an agent compiled the business request correctly.

## 5. Optional canonical hydration in Snowflake

The evaluator can remain local. If it needs a private Snowflake copy, the pack includes canonical DDL, CSVs and `canonical-manifest.json`. Use a separate evaluator connection and an empty private schema:

```sh
python3 src/hydrate_truth.py \
  --private-root data/private_evaluator \
  --connection YOUR_EVALUATOR_CONNECTION \
  --schema YOUR_PRIVATE_DB.SYNTH_TRUTH
```

This verifies fingerprints, creates the model and inserts the data in a transaction, refusing to append to nonempty tables. It uses parameterised inserts and does not require another external stage. No role/grant isolation is established automatically. Use separate credentials and validate effective access before exposing the builder to any source files.

## 6. Operational acceptance still to do

Record actual source availability, start/completion time, release identity and result status for each real run. S2 must be available by 06:30 UTC and S1 by 07:00 UTC under the pilot assumption. Test late/missing deliveries, a failed batch and a repaired replay. Configure weekly Monday S5 execution and its agreed business deadline. Demonstrate an observable notification for percentage alerts and S3/S4 exceptions. A local timestamp or a SQL result alone does not prove these gates.

No scheduler or notification system is deployed by these scripts. This remains explicit in `TODO.md`.
