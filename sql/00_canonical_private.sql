-- Run only as the evaluator in a private database. Never grant this schema to the builder.

CREATE SCHEMA IF NOT EXISTS SYNTH_TRUTH;

USE SCHEMA SYNTH_TRUTH;

CREATE TABLE IF NOT EXISTS hcp (
  hcp_id VARCHAR NOT NULL,
  display_name VARCHAR NOT NULL,
  speciality VARCHAR NOT NULL,
  country VARCHAR NOT NULL,
  postal_sector VARCHAR NOT NULL,
  active BOOLEAN NOT NULL,
  PRIMARY KEY (hcp_id)
);

CREATE TABLE IF NOT EXISTS hco (
  hco_id VARCHAR NOT NULL,
  organisation_name VARCHAR NOT NULL,
  country VARCHAR NOT NULL,
  PRIMARY KEY (hco_id)
);

CREATE TABLE IF NOT EXISTS affiliation (
  affiliation_id VARCHAR NOT NULL,
  hcp_id VARCHAR NOT NULL,
  hco_id VARCHAR NOT NULL,
  relationship_type VARCHAR NOT NULL,
  is_primary BOOLEAN NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE,
  PRIMARY KEY (affiliation_id),
  FOREIGN KEY (hcp_id) REFERENCES hcp (hcp_id),
  FOREIGN KEY (hco_id) REFERENCES hco (hco_id)
);

CREATE TABLE IF NOT EXISTS product (
  product_id VARCHAR NOT NULL,
  product_name VARCHAR NOT NULL,
  active BOOLEAN NOT NULL,
  PRIMARY KEY (product_id)
);

CREATE TABLE IF NOT EXISTS product_hierarchy (
  product_id VARCHAR NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE,
  brand VARCHAR NOT NULL,
  therapy VARCHAR NOT NULL,
  PRIMARY KEY (product_id, effective_from),
  FOREIGN KEY (product_id) REFERENCES product (product_id)
);

CREATE TABLE IF NOT EXISTS territory (
  territory_id VARCHAR NOT NULL,
  territory_name VARCHAR NOT NULL,
  PRIMARY KEY (territory_id)
);

CREATE TABLE IF NOT EXISTS representative (
  rep_id VARCHAR NOT NULL,
  rep_name VARCHAR NOT NULL,
  PRIMARY KEY (rep_id)
);

CREATE TABLE IF NOT EXISTS rep_territory (
  rep_id VARCHAR NOT NULL,
  territory_id VARCHAR NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE,
  PRIMARY KEY (rep_id, territory_id, effective_from),
  FOREIGN KEY (rep_id) REFERENCES representative (rep_id),
  FOREIGN KEY (territory_id) REFERENCES territory (territory_id)
);

CREATE TABLE IF NOT EXISTS hcp_territory (
  assignment_id VARCHAR NOT NULL,
  hcp_id VARCHAR NOT NULL,
  territory_id VARCHAR NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE,
  PRIMARY KEY (assignment_id),
  FOREIGN KEY (hcp_id) REFERENCES hcp (hcp_id),
  FOREIGN KEY (territory_id) REFERENCES territory (territory_id)
);

CREATE TABLE IF NOT EXISTS interaction (
  interaction_id VARCHAR NOT NULL,
  version_no NUMBER NOT NULL,
  hcp_id VARCHAR NOT NULL,
  rep_id VARCHAR NOT NULL,
  primary_product_id VARCHAR NOT NULL,
  occurred_at TIMESTAMP_NTZ NOT NULL,
  channel VARCHAR NOT NULL,
  approval VARCHAR NOT NULL,
  duration_minutes NUMBER NOT NULL,
  modified_at TIMESTAMP_NTZ NOT NULL,
  operation VARCHAR NOT NULL,
  delivery_batch VARCHAR NOT NULL,
  PRIMARY KEY (interaction_id, version_no),
  FOREIGN KEY (hcp_id) REFERENCES hcp (hcp_id),
  FOREIGN KEY (rep_id) REFERENCES representative (rep_id),
  FOREIGN KEY (primary_product_id) REFERENCES product (product_id)
);

CREATE TABLE IF NOT EXISTS interaction_product (
  interaction_id VARCHAR NOT NULL,
  version_no NUMBER NOT NULL,
  product_id VARCHAR NOT NULL,
  detail_rank NUMBER NOT NULL,
  PRIMARY KEY (interaction_id, version_no, product_id),
  FOREIGN KEY (product_id) REFERENCES product (product_id),
  FOREIGN KEY (interaction_id, version_no) REFERENCES interaction (interaction_id, version_no)
);

CREATE TABLE IF NOT EXISTS consent_event (
  consent_id VARCHAR NOT NULL,
  hcp_id VARCHAR NOT NULL,
  channel VARCHAR NOT NULL,
  purpose VARCHAR NOT NULL,
  status VARCHAR NOT NULL,
  effective_at TIMESTAMP_NTZ NOT NULL,
  sequence_no NUMBER NOT NULL,
  delivery_batch VARCHAR NOT NULL,
  PRIMARY KEY (consent_id),
  FOREIGN KEY (hcp_id) REFERENCES hcp (hcp_id)
);

CREATE TABLE IF NOT EXISTS campaign (
  campaign_id VARCHAR NOT NULL,
  product_id VARCHAR NOT NULL,
  start_date DATE NOT NULL,
  end_date_exclusive DATE NOT NULL,
  status VARCHAR NOT NULL,
  PRIMARY KEY (campaign_id),
  FOREIGN KEY (product_id) REFERENCES product (product_id)
);

CREATE TABLE IF NOT EXISTS campaign_member (
  membership_id VARCHAR NOT NULL,
  campaign_id VARCHAR NOT NULL,
  hcp_id VARCHAR NOT NULL,
  member_status VARCHAR NOT NULL,
  PRIMARY KEY (membership_id),
  FOREIGN KEY (campaign_id) REFERENCES campaign (campaign_id),
  FOREIGN KEY (hcp_id) REFERENCES hcp (hcp_id)
);

CREATE TABLE IF NOT EXISTS rx_sales (
  observation_id VARCHAR NOT NULL,
  version_no NUMBER NOT NULL,
  hcp_id VARCHAR NOT NULL,
  product_id VARCHAR NOT NULL,
  week_ending DATE NOT NULL,
  trx_count NUMBER NOT NULL,
  nrx_count NUMBER NOT NULL,
  sales_units NUMBER NOT NULL,
  PRIMARY KEY (observation_id, version_no),
  FOREIGN KEY (hcp_id) REFERENCES hcp (hcp_id),
  FOREIGN KEY (product_id) REFERENCES product (product_id)
);

CREATE TABLE IF NOT EXISTS source_identity (
  entity_type VARCHAR NOT NULL,
  canonical_id VARCHAR NOT NULL,
  source VARCHAR NOT NULL,
  source_id VARCHAR NOT NULL,
  link_token VARCHAR NOT NULL,
  PRIMARY KEY (entity_type, source, source_id)
);
