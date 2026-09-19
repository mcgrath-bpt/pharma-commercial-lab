-- Execute with a client configured to STOP on the first SQL error.

-- Single loader only. Stage must expose the public_s3 tree at its URL root.

CREATE SCHEMA IF NOT EXISTS LAB_DB.PHARMA_CRAWL;

USE SCHEMA LAB_DB.PHARMA_CRAWL;

ALTER SESSION SET TIMEZONE = 'UTC';

CREATE FILE FORMAT IF NOT EXISTS LAB_CSV_V1 TYPE=CSV COMPRESSION=NONE FIELD_DELIMITER=',' RECORD_DELIMITER='\n' SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"' ESCAPE_UNENCLOSED_FIELD=NONE EMPTY_FIELD_AS_NULL=TRUE NULL_IF=('') ERROR_ON_COLUMN_COUNT_MISMATCH=TRUE ENCODING='UTF8';

CREATE TABLE IF NOT EXISTS LAB_BATCH_AUDIT (batch_id VARCHAR, manifest_sha256 VARCHAR, available_at TIMESTAMP_NTZ, loaded_at TIMESTAMP_LTZ, status VARCHAR);

CREATE TABLE IF NOT EXISTS LAB_FILE_AUDIT (batch_id VARCHAR, file_key VARCHAR, expected_sha256 VARCHAR, expected_rows NUMBER, manifest_sha256 VARCHAR);

EXECUTE IMMEDIATE $$ DECLARE bad_release EXCEPTION (-20001, 'Batch ID already bound to different manifest'); n NUMBER; BEGIN SELECT COUNT(*) INTO :n FROM LAB_BATCH_AUDIT WHERE batch_id='b002' AND manifest_sha256<>'42f858c2c95b945d77801815ac13cb6a7460385ebcdc1716cf9d429429d52f5b'; IF (n>0) THEN RAISE bad_release; END IF; END; $$;

CREATE TABLE IF NOT EXISTS RAW_B002_IQVIA_LIKE_RX_WEEKLY (OBSERVATION_KEY VARCHAR, PROVIDER_KEY VARCHAR, PRODUCT_CODE VARCHAR, WEEK_ENDING VARCHAR, TRX_COUNT VARCHAR, NRX_COUNT VARCHAR, SALES_UNITS VARCHAR, VERSION_NO VARCHAR);

COPY INTO RAW_B002_IQVIA_LIKE_RX_WEEKLY FROM @LAB_DB.INGEST.EXISTING_S3_STAGE FILES=('synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/rx_weekly/batch=b002/part-00001.csv') FILE_FORMAT=(FORMAT_NAME='LAB_DB.PHARMA_CRAWL.LAB_CSV_V1') ON_ERROR='ABORT_STATEMENT' FORCE=FALSE;

EXECUTE IMMEDIATE $$ DECLARE bad_count EXCEPTION (-20002, 'Loaded row count differs from manifest: RAW_B002_IQVIA_LIKE_RX_WEEKLY'); n NUMBER; BEGIN SELECT COUNT(*) INTO :n FROM RAW_B002_IQVIA_LIKE_RX_WEEKLY; IF (n<>1) THEN RAISE bad_count; END IF; END; $$;

CREATE TABLE IF NOT EXISTS RAW_B002_SALESFORCE_LIKE_CONSENT (PREFERENCE_KEY VARCHAR, CONTACT_KEY VARCHAR, CHANNEL VARCHAR, PURPOSE VARCHAR, STATUS VARCHAR, EFFECTIVE_AT VARCHAR, SEQUENCE_NO VARCHAR);

COPY INTO RAW_B002_SALESFORCE_LIKE_CONSENT FROM @LAB_DB.INGEST.EXISTING_S3_STAGE FILES=('synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/consent/batch=b002/part-00001.csv') FILE_FORMAT=(FORMAT_NAME='LAB_DB.PHARMA_CRAWL.LAB_CSV_V1') ON_ERROR='ABORT_STATEMENT' FORCE=FALSE;

EXECUTE IMMEDIATE $$ DECLARE bad_count EXCEPTION (-20002, 'Loaded row count differs from manifest: RAW_B002_SALESFORCE_LIKE_CONSENT'); n NUMBER; BEGIN SELECT COUNT(*) INTO :n FROM RAW_B002_SALESFORCE_LIKE_CONSENT; IF (n<>2) THEN RAISE bad_count; END IF; END; $$;

CREATE TABLE IF NOT EXISTS RAW_B002_VEEVA_LIKE_ACTIVITY (ACTIVITY_KEY VARCHAR, CUSTOMER_KEY VARCHAR, PRIMARY_PRODUCT_CODE VARCHAR, OCCURRED_AT VARCHAR, CHANNEL VARCHAR, APPROVAL VARCHAR, DURATION_MINUTES VARCHAR, SOURCE_VERSION VARCHAR, MODIFIED_AT VARCHAR, OPERATION VARCHAR);

COPY INTO RAW_B002_VEEVA_LIKE_ACTIVITY FROM @LAB_DB.INGEST.EXISTING_S3_STAGE FILES=('synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity/batch=b002/part-00001.csv') FILE_FORMAT=(FORMAT_NAME='LAB_DB.PHARMA_CRAWL.LAB_CSV_V1') ON_ERROR='ABORT_STATEMENT' FORCE=FALSE;

EXECUTE IMMEDIATE $$ DECLARE bad_count EXCEPTION (-20002, 'Loaded row count differs from manifest: RAW_B002_VEEVA_LIKE_ACTIVITY'); n NUMBER; BEGIN SELECT COUNT(*) INTO :n FROM RAW_B002_VEEVA_LIKE_ACTIVITY; IF (n<>6) THEN RAISE bad_count; END IF; END; $$;

CREATE TABLE IF NOT EXISTS RAW_B002_VEEVA_LIKE_ACTIVITY_PRODUCT (ACTIVITY_KEY VARCHAR, SOURCE_VERSION VARCHAR, PRODUCT_CODE VARCHAR, DETAIL_RANK VARCHAR);

COPY INTO RAW_B002_VEEVA_LIKE_ACTIVITY_PRODUCT FROM @LAB_DB.INGEST.EXISTING_S3_STAGE FILES=('synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity_product/batch=b002/part-00001.csv') FILE_FORMAT=(FORMAT_NAME='LAB_DB.PHARMA_CRAWL.LAB_CSV_V1') ON_ERROR='ABORT_STATEMENT' FORCE=FALSE;

EXECUTE IMMEDIATE $$ DECLARE bad_count EXCEPTION (-20002, 'Loaded row count differs from manifest: RAW_B002_VEEVA_LIKE_ACTIVITY_PRODUCT'); n NUMBER; BEGIN SELECT COUNT(*) INTO :n FROM RAW_B002_VEEVA_LIKE_ACTIVITY_PRODUCT; IF (n<>6) THEN RAISE bad_count; END IF; END; $$;

BEGIN TRANSACTION;

INSERT INTO LAB_FILE_AUDIT SELECT 'b002','synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/rx_weekly/batch=b002/part-00001.csv','69ebc15eb062c576de87cb890c0e7abb35a2b077af2c5ff7f31f74281d6da02c',1,'42f858c2c95b945d77801815ac13cb6a7460385ebcdc1716cf9d429429d52f5b' WHERE NOT EXISTS (SELECT 1 FROM LAB_FILE_AUDIT WHERE batch_id='b002' AND file_key='synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/rx_weekly/batch=b002/part-00001.csv');

INSERT INTO LAB_FILE_AUDIT SELECT 'b002','synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/consent/batch=b002/part-00001.csv','278c08d9c2a891227cedb6ac763e51d81d57f615ac4d3efa80bf7e459afe4df1',2,'42f858c2c95b945d77801815ac13cb6a7460385ebcdc1716cf9d429429d52f5b' WHERE NOT EXISTS (SELECT 1 FROM LAB_FILE_AUDIT WHERE batch_id='b002' AND file_key='synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/consent/batch=b002/part-00001.csv');

INSERT INTO LAB_FILE_AUDIT SELECT 'b002','synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity/batch=b002/part-00001.csv','89917e7c7494a658e540e51e3a38102e865778569ccb3f4f8b475e9c00194d72',6,'42f858c2c95b945d77801815ac13cb6a7460385ebcdc1716cf9d429429d52f5b' WHERE NOT EXISTS (SELECT 1 FROM LAB_FILE_AUDIT WHERE batch_id='b002' AND file_key='synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity/batch=b002/part-00001.csv');

INSERT INTO LAB_FILE_AUDIT SELECT 'b002','synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity_product/batch=b002/part-00001.csv','edf11c5ac71b367c5bccfcf765a31581bc6ce71b5f2425f48033f4de7c472de6',6,'42f858c2c95b945d77801815ac13cb6a7460385ebcdc1716cf9d429429d52f5b' WHERE NOT EXISTS (SELECT 1 FROM LAB_FILE_AUDIT WHERE batch_id='b002' AND file_key='synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity_product/batch=b002/part-00001.csv');

INSERT INTO LAB_BATCH_AUDIT SELECT 'b002','42f858c2c95b945d77801815ac13cb6a7460385ebcdc1716cf9d429429d52f5b',TO_TIMESTAMP_NTZ('2026-09-15T05:00:00Z'),CURRENT_TIMESTAMP(),'LOADED' WHERE NOT EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT WHERE batch_id='b002');

COMMIT;

CREATE OR REPLACE VIEW SRC_IQVIA_LIKE_AFFILIATION AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/affiliation/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_IQVIA_LIKE_AFFILIATION r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_IQVIA_LIKE_ORGANISATION AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/organisation/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_IQVIA_LIKE_ORGANISATION r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_IQVIA_LIKE_PRODUCT AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/product/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_IQVIA_LIKE_PRODUCT r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_IQVIA_LIKE_PROVIDER AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/provider/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_IQVIA_LIKE_PROVIDER r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_IQVIA_LIKE_RX_WEEKLY AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/rx_weekly/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_IQVIA_LIKE_RX_WEEKLY r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED')
UNION ALL
SELECT r.*, 'b002' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-15T05:00:00Z') AS _available_at, 'incremental' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/iqvia_like/rx_weekly/batch=b002/part-00001.csv' AS _file_key FROM RAW_B002_IQVIA_LIKE_RX_WEEKLY r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b002' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_MANUAL_TERRITORY_MAPPING AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/manual/territory_mapping/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_MANUAL_TERRITORY_MAPPING r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_SALESFORCE_LIKE_CAMPAIGN AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/campaign/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_SALESFORCE_LIKE_CAMPAIGN r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_SALESFORCE_LIKE_CAMPAIGN_MEMBER AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/campaign_member/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_SALESFORCE_LIKE_CAMPAIGN_MEMBER r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_SALESFORCE_LIKE_CONSENT AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/consent/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_SALESFORCE_LIKE_CONSENT r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED')
UNION ALL
SELECT r.*, 'b002' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-15T05:00:00Z') AS _available_at, 'incremental' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/consent/batch=b002/part-00001.csv' AS _file_key FROM RAW_B002_SALESFORCE_LIKE_CONSENT r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b002' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_SALESFORCE_LIKE_CONTACT AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/salesforce_like/contact/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_SALESFORCE_LIKE_CONTACT r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_VEEVA_LIKE_ACTIVITY AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_VEEVA_LIKE_ACTIVITY r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED')
UNION ALL
SELECT r.*, 'b002' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-15T05:00:00Z') AS _available_at, 'incremental' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity/batch=b002/part-00001.csv' AS _file_key FROM RAW_B002_VEEVA_LIKE_ACTIVITY r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b002' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_VEEVA_LIKE_ACTIVITY_PRODUCT AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity_product/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_VEEVA_LIKE_ACTIVITY_PRODUCT r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED')
UNION ALL
SELECT r.*, 'b002' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-15T05:00:00Z') AS _available_at, 'incremental' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/activity_product/batch=b002/part-00001.csv' AS _file_key FROM RAW_B002_VEEVA_LIKE_ACTIVITY_PRODUCT r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b002' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_VEEVA_LIKE_CUSTOMER AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/customer/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_VEEVA_LIKE_CUSTOMER r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_VEEVA_LIKE_STAFF AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/staff/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_VEEVA_LIKE_STAFF r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');

CREATE OR REPLACE VIEW SRC_VEEVA_LIKE_TERRITORY AS
SELECT r.*, 'b001' AS _batch_id, TO_TIMESTAMP_NTZ('2026-09-14T05:00:00Z') AS _available_at, 'bootstrap' AS _mode, 'synthetic/pharma/pharma-lab-0.1.0/sources/veeva_like/territory/batch=b001/part-00001.csv' AS _file_key FROM RAW_B001_VEEVA_LIKE_TERRITORY r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id='b001' AND a.status='LOADED');
