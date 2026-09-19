-- Draft Snowflake reference for all five scenarios, to execute after a loader.
-- No Snowflake account was used to validate this file. STOP on the first error.
-- Session-local derived tables are intentional for Crawl; publishing is separate.
-- USE SCHEMA <your isolated database.schema> before running this file.
ALTER SESSION SET TIMEZONE = 'UTC';
SET AS_OF = '2026-09-15T06:00:00Z'; -- b001: 2026-09-14T06:00:00Z

CREATE OR REPLACE TEMP TABLE APPROVED_CUSTOMER AS
SELECT DISTINCT provider_key,link_token FROM SRC_IQVIA_LIKE_PROVIDER
WHERE active='true' AND _available_at<=TO_TIMESTAMP_NTZ($AS_OF);
CREATE OR REPLACE TEMP TABLE UNIQUE_TOKEN AS
SELECT link_token,MIN(provider_key) provider_key FROM APPROVED_CUSTOMER
WHERE link_token IS NOT NULL GROUP BY link_token HAVING COUNT(DISTINCT provider_key)=1;
CREATE OR REPLACE TEMP TABLE CRM_MAP AS
SELECT DISTINCT c.customer_key,u.provider_key FROM SRC_VEEVA_LIKE_CUSTOMER c
JOIN UNIQUE_TOKEN u ON c.match_token=u.link_token
WHERE c._available_at<=TO_TIMESTAMP_NTZ($AS_OF);
CREATE OR REPLACE TEMP TABLE SF_MAP AS
SELECT DISTINCT c.contact_key,u.provider_key FROM SRC_SALESFORCE_LIKE_CONTACT c
JOIN UNIQUE_TOKEN u ON c.match_token=u.link_token
WHERE c._available_at<=TO_TIMESTAMP_NTZ($AS_OF);
CREATE OR REPLACE TEMP TABLE CURRENT_PRODUCT AS
SELECT DISTINCT product_code,brand,therapy FROM SRC_IQVIA_LIKE_PRODUCT
WHERE active='true' AND valid_from::DATE<=TO_DATE(TO_TIMESTAMP_NTZ($AS_OF))
AND (valid_to IS NULL OR TO_DATE(TO_TIMESTAMP_NTZ($AS_OF))<valid_to::DATE)
AND _available_at<=TO_TIMESTAMP_NTZ($AS_OF);

CREATE OR REPLACE TEMP TABLE ACTIVITY_VERSION AS
SELECT DISTINCT activity_key,customer_key,primary_product_code,occurred_at,channel,approval,
duration_minutes,source_version,modified_at,operation,_available_at,_mode
FROM SRC_VEEVA_LIKE_ACTIVITY WHERE _available_at<=TO_TIMESTAMP_NTZ($AS_OF);
-- Fail conflicting versions before choosing a winner. A row-number tie breaker
-- would merely conceal the source defect.
EXECUTE IMMEDIATE $$
DECLARE bad EXCEPTION (-20003,'Conflicting interaction versions'); n NUMBER;
BEGIN
  SELECT COUNT(*) INTO :n FROM (
    SELECT activity_key,source_version FROM (
      SELECT DISTINCT activity_key,customer_key,primary_product_code,occurred_at,channel,
        approval,duration_minutes,source_version,modified_at,operation FROM ACTIVITY_VERSION
    ) GROUP BY activity_key,source_version HAVING COUNT(*)>1
  );
  IF (n>0) THEN RAISE bad; END IF;
END; $$;

CREATE OR REPLACE TEMP TABLE ACTIVITY_CLASSIFIED AS
SELECT *, CASE
 WHEN activity_key IS NULL OR customer_key IS NULL OR primary_product_code IS NULL
   OR occurred_at IS NULL OR modified_at IS NULL THEN 'MISSING_REQUIRED'
 WHEN TRY_TO_TIMESTAMP_NTZ(occurred_at) IS NULL OR TRY_TO_TIMESTAMP_NTZ(modified_at) IS NULL
   OR TRY_TO_NUMBER(duration_minutes) IS NULL OR TRY_TO_NUMBER(source_version) IS NULL THEN 'INVALID_TYPE'
 WHEN TRY_TO_NUMBER(duration_minutes)<0 OR TRY_TO_TIMESTAMP_NTZ(occurred_at)>TO_TIMESTAMP_NTZ($AS_OF)
   OR TRY_TO_TIMESTAMP_NTZ(modified_at)>_available_at OR operation NOT IN ('UPSERT','DELETE') THEN 'INVALID_VALUE'
 WHEN _mode<>'bootstrap' AND DATEDIFF(day,
   IFF(TRY_TO_NUMBER(source_version)>1,TRY_TO_TIMESTAMP_NTZ(modified_at),TRY_TO_TIMESTAMP_NTZ(occurred_at)),_available_at)>7 THEN 'LATE_BEYOND_WINDOW'
 ELSE 'ACCEPT' END AS disposition
FROM ACTIVITY_VERSION;
CREATE OR REPLACE TEMP TABLE INTERACTION_LATEST AS
SELECT * FROM ACTIVITY_CLASSIFIED WHERE disposition='ACCEPT'
QUALIFY ROW_NUMBER() OVER(PARTITION BY activity_key ORDER BY source_version::NUMBER DESC,_available_at ASC)=1;
CREATE OR REPLACE TEMP TABLE GOLD_S04_INTERACTION AS
SELECT activity_key,customer_key,primary_product_code,occurred_at,channel,
duration_minutes::NUMBER duration_minutes,source_version::NUMBER source_version
FROM INTERACTION_LATEST WHERE operation<>'DELETE';
CREATE OR REPLACE TEMP TABLE ELIGIBLE AS
SELECT a.*,m.provider_key FROM INTERACTION_LATEST a LEFT JOIN CRM_MAP m USING(customer_key)
WHERE a.operation<>'DELETE' AND a.approval='APPROVED';
CREATE OR REPLACE TEMP TABLE DETAIL AS
SELECT DISTINCT activity_key,source_version::NUMBER source_version,product_code
FROM SRC_VEEVA_LIKE_ACTIVITY_PRODUCT WHERE _available_at<=TO_TIMESTAMP_NTZ($AS_OF);
CREATE OR REPLACE TEMP TABLE CONSENT_CANDIDATE AS
SELECT DISTINCT m.provider_key,c.channel,c.status,c.effective_at,c.sequence_no::NUMBER sequence_no
FROM SRC_SALESFORCE_LIKE_CONSENT c JOIN SF_MAP m USING(contact_key)
WHERE c.purpose='COMMERCIAL' AND c.effective_at::TIMESTAMP_NTZ<=TO_TIMESTAMP_NTZ($AS_OF)
AND c._available_at<=TO_TIMESTAMP_NTZ($AS_OF);
EXECUTE IMMEDIATE $$
DECLARE bad EXCEPTION (-20004,'Ambiguous current product or consent'); n NUMBER;
BEGIN
 SELECT COUNT(*) INTO :n FROM (
   SELECT product_code FROM CURRENT_PRODUCT GROUP BY product_code HAVING COUNT(*)>1
   UNION ALL
   SELECT provider_key FROM CONSENT_CANDIDATE GROUP BY provider_key,channel,effective_at,sequence_no HAVING COUNT(DISTINCT status)>1
 );
 IF (n>0) THEN RAISE bad; END IF;
END; $$;
CREATE OR REPLACE TEMP TABLE CURRENT_CONSENT AS
SELECT * FROM CONSENT_CANDIDATE
QUALIFY ROW_NUMBER() OVER(PARTITION BY provider_key,channel ORDER BY effective_at::TIMESTAMP_NTZ DESC,sequence_no DESC)=1;
CREATE OR REPLACE TEMP TABLE GOLD_S01_ENGAGEMENT AS
SELECT a.activity_key,a.provider_key customer_key,LEFT(a.occurred_at,10) activity_date,c.status consent_status
FROM ELIGIBLE a JOIN CURRENT_CONSENT c ON a.provider_key=c.provider_key AND a.channel=c.channel
WHERE c.status='GRANTED';
CREATE OR REPLACE TEMP TABLE GOLD_S02_PRODUCT_ACTIVITY AS
SELECT a.provider_key customer_key,p.product_code,LEFT(a.occurred_at,10) activity_date,
p.brand,p.therapy,COUNT(DISTINCT a.activity_key) interaction_count
FROM ELIGIBLE a JOIN DETAIL d ON a.activity_key=d.activity_key AND a.source_version::NUMBER=d.source_version
JOIN CURRENT_PRODUCT p ON d.product_code=p.product_code WHERE a.provider_key IS NOT NULL
GROUP BY a.provider_key,p.product_code,LEFT(a.occurred_at,10),p.brand,p.therapy;

CREATE OR REPLACE TEMP TABLE TERRITORY_CANDIDATE AS
SELECT DISTINCT provider_key,territory_code,effective_from FROM SRC_MANUAL_TERRITORY_MAPPING
WHERE effective_from::DATE<=TO_DATE(TO_TIMESTAMP_NTZ($AS_OF))
AND (effective_to IS NULL OR TO_DATE(TO_TIMESTAMP_NTZ($AS_OF))<effective_to::DATE)
AND _available_at<=TO_TIMESTAMP_NTZ($AS_OF)
QUALIFY DENSE_RANK() OVER(PARTITION BY provider_key ORDER BY effective_from::DATE DESC)=1;
EXECUTE IMMEDIATE $$
DECLARE bad EXCEPTION (-20005,'Duplicate current or unknown territory'); n NUMBER;
BEGIN
 SELECT COUNT(*) INTO :n FROM (
   SELECT provider_key FROM TERRITORY_CANDIDATE GROUP BY provider_key HAVING COUNT(DISTINCT territory_code)>1
   UNION ALL
   SELECT provider_key FROM TERRITORY_CANDIDATE WHERE territory_code NOT IN (SELECT territory_code FROM SRC_VEEVA_LIKE_TERRITORY)
 );
 IF (n>0) THEN RAISE bad; END IF;
END; $$;
CREATE OR REPLACE TEMP TABLE GOLD_S03_CUSTOMER_TERRITORY AS
SELECT c.provider_key customer_key,COALESCE(t.territory_code,'') territory_code,
IFF(t.territory_code IS NULL,'MISSING','ASSIGNED') assignment_status
FROM APPROVED_CUSTOMER c LEFT JOIN TERRITORY_CANDIDATE t USING(provider_key);

CREATE OR REPLACE TEMP TABLE CAMPAIGN_MEMBER AS
SELECT DISTINCT campaign_key,contact_key FROM SRC_SALESFORCE_LIKE_CAMPAIGN_MEMBER
WHERE member_status='ENROLLED' AND _available_at<=TO_TIMESTAMP_NTZ($AS_OF);
CREATE OR REPLACE TEMP TABLE CAMPAIGN AS
SELECT DISTINCT campaign_key,product_code,start_date,end_date_exclusive,status
FROM SRC_SALESFORCE_LIKE_CAMPAIGN WHERE status<>'CANCELLED' AND _available_at<=TO_TIMESTAMP_NTZ($AS_OF);
CREATE OR REPLACE TEMP TABLE GOLD_S05_CAMPAIGN AS
SELECT c.campaign_key,m.provider_key customer_key,c.product_code,
IFF(COUNT(DISTINCT a.activity_key)>0,'true','false') contacted,
COUNT(DISTINCT a.activity_key) qualifying_interactions
FROM CAMPAIGN c JOIN CAMPAIGN_MEMBER cm USING(campaign_key)
JOIN SF_MAP m USING(contact_key) JOIN CURRENT_PRODUCT p ON c.product_code=p.product_code
LEFT JOIN (
 SELECT e.activity_key,e.provider_key,e.occurred_at,d.product_code FROM ELIGIBLE e
 JOIN DETAIL d ON e.activity_key=d.activity_key AND e.source_version::NUMBER=d.source_version
) a ON a.provider_key=m.provider_key AND a.product_code=c.product_code
 AND LEFT(a.occurred_at,10)>=c.start_date AND LEFT(a.occurred_at,10)<c.end_date_exclusive
GROUP BY c.campaign_key,m.provider_key,c.product_code;

CREATE OR REPLACE TEMP TABLE UNKNOWN_PRODUCT_ACTIVITY AS
SELECT DISTINCT a.activity_key FROM ELIGIBLE a
LEFT JOIN DETAIL d ON a.activity_key=d.activity_key AND a.source_version::NUMBER=d.source_version
LEFT JOIN CURRENT_PRODUCT p ON d.product_code=p.product_code WHERE p.product_code IS NULL;
CREATE OR REPLACE TEMP TABLE GOLD_EXCEPTIONS AS
SELECT DISTINCT 'S04' scenario,activity_key record_key,disposition reason FROM ACTIVITY_CLASSIFIED WHERE disposition<>'ACCEPT'
UNION
SELECT 'S01',activity_key,'UNMATCHED_CUSTOMER' FROM ELIGIBLE WHERE provider_key IS NULL
UNION
SELECT 'S01',a.activity_key,IFF(c.provider_key IS NULL,'MISSING_CONSENT','WITHDRAWN_OR_UNKNOWN_CONSENT')
FROM ELIGIBLE a LEFT JOIN CURRENT_CONSENT c ON a.provider_key=c.provider_key AND a.channel=c.channel
WHERE a.provider_key IS NOT NULL AND (c.provider_key IS NULL OR c.status<>'GRANTED')
UNION
SELECT 'S02',activity_key,'UNKNOWN_PRODUCT' FROM UNKNOWN_PRODUCT_ACTIVITY
UNION
SELECT 'S02',activity_key,'UNMATCHED_CUSTOMER' FROM ELIGIBLE WHERE provider_key IS NULL
UNION
SELECT 'S03',customer_key,'MISSING_TERRITORY' FROM GOLD_S03_CUSTOMER_TERRITORY WHERE assignment_status='MISSING'
UNION
SELECT 'S05',c.campaign_key||'|'||cm.contact_key,'UNMATCHED_MEMBER'
FROM CAMPAIGN c JOIN CAMPAIGN_MEMBER cm USING(campaign_key) LEFT JOIN SF_MAP m USING(contact_key) WHERE m.provider_key IS NULL
UNION
SELECT 'S05',c.campaign_key,'UNKNOWN_PRODUCT' FROM CAMPAIGN c LEFT JOIN CURRENT_PRODUCT p USING(product_code) WHERE p.product_code IS NULL;

CREATE OR REPLACE TEMP TABLE DQ_COUNTS AS
SELECT 'S01' scenario,'ALL' scope,COALESCE(COUNT_IF(provider_key IS NULL),0) numerator,COUNT(*) denominator,0.02::NUMBER(3,2) threshold FROM ELIGIBLE
UNION ALL
SELECT 'S02','ALL',(SELECT COUNT(*) FROM UNKNOWN_PRODUCT_ACTIVITY),COUNT(*),0.01 FROM ELIGIBLE
UNION ALL
SELECT 'S05',c.campaign_key,COALESCE(COUNT_IF(cm.contact_key IS NOT NULL AND m.provider_key IS NULL),0),COUNT(cm.contact_key),0.05
FROM CAMPAIGN c LEFT JOIN CAMPAIGN_MEMBER cm USING(campaign_key) LEFT JOIN SF_MAP m USING(contact_key) GROUP BY c.campaign_key;
CREATE OR REPLACE TEMP TABLE GOLD_DQ AS
SELECT *,CASE WHEN denominator=0 THEN 'NO_DATA' WHEN numerator>denominator*threshold THEN 'ALERT' ELSE 'PASS' END status FROM DQ_COUNTS;

-- Commercial observations are a useful supporting hydration check, not a sixth scenario.
CREATE OR REPLACE TEMP TABLE RX_LATEST AS
SELECT * FROM SRC_IQVIA_LIKE_RX_WEEKLY WHERE _available_at<=TO_TIMESTAMP_NTZ($AS_OF)
QUALIFY ROW_NUMBER() OVER(PARTITION BY observation_key ORDER BY version_no::NUMBER DESC)=1;
-- Export named GOLD_* tables with lowercase headers matching contracts/output-columns.json.
-- Reconcile all seven tables before publishing. Alerts do not imply failed row correctness.
