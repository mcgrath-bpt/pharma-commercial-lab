# Five acceptance contracts

The business requests below were recovered from **Plan Guarded Snowflake Pipelines**. The implementation decisions make their ambiguous parts executable; they do not silently revise their thresholds.

## S1 · Customer engagement + consent

> I need a daily customer engagement dataset combining approved CRM activity and consent information. Keep the most recent consent status, exclude withdrawn customers, make it available by 07:00 each morning and alert us if more than 2% of CRM records fail to match.

**Output:** `s01_engagement`, one approved, nondeleted interaction per active approved customer with current GRANTED consent for the interaction channel and COMMERCIAL purpose. The fixture uses EMAIL. Historical engagement is filtered using consent at the reporting cut-off, not consent at interaction time. Missing, unknown and withdrawn consent are excluded with separate reasons. Future events do not override current consent.

**Identity DQ:** denominator is the distinct latest, structurally valid, accepted, approved, nondeleted CRM interactions observed by the cut-off, across the reporting history. Numerator is those without a unique active approved customer match, before consent filtering. Missing consent is a separate exception, not a match-rate failure. Alert when numerator / denominator **> 0.02**. Exactly 2% passes. An empty population is `NO_DATA`, not success.


## S2 · Sales activity + product reference

> I need a daily sales activity dataset combining CRM activity with the approved product hierarchy. Keep only valid products, map activity to the current product hierarchy, aggregate to one record per customer, product and day, and make the dataset available by 06:30 each morning. Alert us if more than 1% of activity records reference an unknown product.

**Output:** `s02_product_activity`, unique `(customer_key, product_code, activity_date)`. The measure is distinct interaction count. Product details match the selected interaction version. Keep valid details for uniquely matched active customers and decorate with the hierarchy current at the cut-off. A hierarchy change can restate older dates. Consent is not part of S2's original request.

**Product DQ:** the same eligible interaction population as S1, before customer/product joins. Count each interaction once if it has no details or any unknown/inactive/noncurrent product reference. One multi-product activity does not increase the denominator. Alert at **> 0.01**. If an interaction contains both valid and invalid products, retain its valid details and flag the interaction.


## S3 · Customer master + territory assignment

> Create a current customer-territory dataset using the approved customer master and the monthly territory mapping file. Each active customer should have exactly one current territory. Where multiple assignments exist, use the most recently effective assignment. Flag customers without a territory and fail the pipeline if duplicate current assignments remain.

**Output:** `s03_customer_territory`, one row for every active approved customer, including an empty territory and `MISSING` status when unresolved. Read the named `Territory` worksheet through the adapter; the resulting CSV is the ingestion input. Use `[effective_from, effective_to)` intervals at the cut-off date.

Consider all currently effective assignments, select the maximum effective-from date, collapse exact/semantically identical assignments, and fail if more than one distinct territory remains. A future mapping must not win early. An unknown territory code is a hard error. Missing assignment is an exception; it does not cause that customer to disappear.


## S4 · Interaction feed with late arrivals and corrections

> Create a daily interaction dataset from the CRM activity feed. Include new interactions and corrections to existing interactions, accept records arriving up to seven days late, and retain only the latest version of each interaction. Produce one trusted record per interaction and alert us if required customer, product or interaction dates are missing.

**Output:** `s04_interaction`, unique CRM activity key, latest accepted nondeleted version. This is a feed-level dataset; it includes draft activities and unresolved but present source customer/product identifiers. It retains CRM customer IDs. S1/S2/S5 subsequently apply approval and reference rules.

Bootstrap explicitly loads the declared historical window without a lateness rejection. Subsequent **new** events may arrive up to seven UTC calendar days after the occurred date. **Corrections and tombstones**, identified by version > 1, may arrive up to seven days after their modification date, even when the original interaction is older. Day seven passes; day eight is quarantined. A late rejected correction leaves the previous accepted state unchanged.

Require activity key, customer key, primary product code, occurred time and modification time. Missing fields generate an alertable exception and do not overwrite trusted state. Invalid dates or negative durations are exceptions. Conflicting payloads for one activity/version fail. Higher source version wins regardless of file order; identical redelivery is harmless. A DELETE tombstone suppresses the interaction in all consuming scenarios. Deleting an S3 object is never a business deletion.


## S5 · Campaign effectiveness

> I need a weekly campaign effectiveness dataset combining approved campaign membership, customer interactions and product information. For each campaign and customer, show whether the customer was contacted, the number of qualifying interactions during the campaign period and the associated product. Exclude cancelled campaigns and flag campaigns where more than 5% of members cannot be matched to an approved customer.

**Output:** `s05_campaign`, unique `(campaign_key, customer_key)`; one associated product per campaign in Crawl. Keep enrolled members of noncancelled campaigns with a current valid product and an active approved customer. Include zero-contact members. A qualifying interaction is approved, accepted, nondeleted, has a uniquely resolved customer, discusses the campaign product and occurs in `[campaign.start_date, campaign.end_date_exclusive)`. It must already be delivered by the cut-off.

Reports run weekly, but counts are campaign-to-date through the report cut-off, not merely the last seven days. Consent is not an additional S5 condition. Overlapping campaigns can each count the same qualifying interaction; this is descriptive contact reporting, not causal attribution.

**Member DQ:** per noncancelled campaign, denominator is unique enrolled `(campaign, contact)` memberships before matching. Numerator is members without a unique active approved customer. Alert at **> 0.05**; exactly 5% passes. Duplicate delivery cannot inflate either side. No members gives `NO_DATA`. Unmatched members appear in exceptions rather than as invented customers.


## Comparison and operational gates

Each checkpoint contains seven expected CSVs: five outputs plus `exceptions` and `dq`. Compare full multisets with exact identifiers, strings, booleans and integer measures. Differences in row order do not matter. Duplicate counts do matter. The comparator reports missing and unexpected rows; a changed attribute appears as one of each. Snowflake exports must normalise headers and types using the supplied export tool.

The packaged DQ table covers the three percentage rules. **S3 missing assignments and S4 required-field alerts are represented in `exceptions`, not in percentage DQ rows.** A scheduler/notifier must inspect both files/tables. Do not report the lack of a percentage alert as overall clean data.

S1 and S2 deadlines require real completion timestamps, delivery freshness checks and notification evidence. The local fixture does not establish these operational results. A daily snapshot re-runs over the history delivered to date; per-day run history and publication bookkeeping are Walk work.
