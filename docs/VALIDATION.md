# Validation evidence and limits

The executed evidence is in `evidence/validation-report.json` and `evidence/tests.txt`. The local source reference reads only `public_s3`; the oracle reads only the canonical world plus its explicit projection ledger. Neither calls the other's transformation logic. They share CSV interchange helpers and output column definitions.

The private ledger explicitly labels the late-eight-day and missing-date projections. These labels do not reach the pipeline. The oracle can therefore specify their expected exclusion without repeating the reference implementation's delivery acceptance algorithm. Aggregate and join semantics still reflect the same written business decisions, so hand-checked examples and mutation tests are essential. Agreement between two programmes alone is not mathematical proof of a correct specification.

## Executed checks

- Full row-multiset comparisons for all five outputs, exceptions and DQ at both cut-offs.
- Re-generation with the same seed produces identical core CSV/JSON bytes.
- Canonical PK uniqueness, FK integrity, composite detail references, basic types and interval validity.
- Manifest/header/count/byte/fingerprint checks for both deliveries.
- Duplicate delivery and reversed input order preserve all results.
- Deliveries after an earlier reporting cut-off remain invisible when recomputing that cut-off.
- The uploader refuses unlisted files, including private material accidentally placed in the public directory.
- Same interaction ID/version with different payload fails.
- Ambiguous public identity evidence is not arbitrarily selected.
- Seven-day arrival accepted; eight-day arrival and missing occurred date excluded.
- Recent correction to an old interaction replaces its product; a tombstone removes another interaction.
- Consent withdrawal affects historical current-consent output; a future regrant does not override it.
- Current product hierarchy changes historical decoration at the next cut-off.
- Territory end date is exclusive; equal latest-effective conflicting territories fail.
- Exact 1%, 2% and 5% boundaries pass; a higher numerator alerts; zero denominator is `NO_DATA`.
- Missing, duplicate and changed actual result rows cause reconciliation failure.
- File fingerprint changes, changed headers even with updated hashes, and missing files are rejected.
- XLSX roundtrip yields exactly the staged mapping CSV; formula cells are rejected.

## Checkpoint row counts

| Result | b001 · 14 September | b002 · 15 September |
|---|---:|---:|
| S1 engagement | 281 | 279 |
| S2 product activity | 298 | 299 |
| S3 current customer territory | 99 | 99 |
| S4 trusted interaction | 300 | 301 |
| S5 campaign/customer | 59 | 59 |
| Exceptions | 25 | 30 |
| Percentage DQ results | 5 | 5 |

All comparisons had zero missing or unexpected rows. DQ rows are deliberately mixed PASS/ALERT outcomes: S1's unmatched customer rate breaches 2%, while the fixture's product rate is below 1% and one campaign sits exactly at the 5% boundary. Threshold microtests separately exercise the exact and over-limit cases.

## Not verified here

No S3 calls, Snowflake statements, stage privileges, role isolation, timed jobs, actual notifications or generated-agent deployment were exercised. The supplied SQL is a hand-built baseline for cloud verification. Local replay proves result semantics, not persistent state recovery, service reliability or performance at production volume. The CSV generator does not create new XLSX containers; the delivered workbook is a static input fixture with a tested adapter.

The Python workflow was executed with the environment version recorded in the JSON report. Python 3.10+ is the intended portable minimum; no separate run on every supported Python version was performed.
