# S3 folder and file layout

All paths below are relative to the existing stage URL. If its URL is `s3://bucket/existing-prefix/`, prepend that exact URL to every key. Never copy the private evaluator directory under that stage.

```text
synthetic/pharma/pharma-lab-0.1.0/business_files/territory/territory_mapping_202609.xlsx
synthetic/pharma/pharma-lab-0.1.0/control/b001.manifest.json
synthetic/pharma/pharma-lab-0.1.0/control/b001.ready.json
synthetic/pharma/pharma-lab-0.1.0/control/b002.manifest.json
synthetic/pharma/pharma-lab-0.1.0/control/b002.ready.json
synthetic/pharma/pharma-lab-0.1.0/control/source-contracts.json
synthetic/pharma/pharma-lab-0.1.0/control/territory-adapter.receipt.json
synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/affiliation/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/organisation/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/product/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/provider/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/rx_weekly/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/rx_weekly/batch=b002/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/manual/territory_mapping/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/campaign/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/campaign_member/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/consent/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/consent/batch=b002/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/contact/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity/batch=b002/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity_product/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity_product/batch=b002/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/customer/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/staff/batch=b001/part-00001.csv
synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/territory/batch=b001/part-00001.csv
```

Each CSV file has one UTF-8 header, comma delimiters, double-quote escaping and LF record delimiters. Empty field is null. There is one part per source/batch in Crawl. Scale by adding manifest-listed parts while preserving entity/version semantics. Manifests currently list only loadable CSVs; the original XLSX and adapter receipt are provenance artefacts outside the COPY lists.

The bootstrap manifest contains 15 source files and the incremental manifest contains four. Full source records are in source subdirectories; manifests and ready markers are in control. Delivery mode is explicit, so a historical bootstrap is not misclassified as a late incremental event.
