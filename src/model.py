"""Canonical schema. PKs and FKs are explicitly verified locally, not assumed enforced."""
from common import ROOT, write_json

# name: (columns with Snowflake types, primary key, foreign keys, grain)
MODEL = {
    "hcp": ("hcp_id VARCHAR,display_name VARCHAR,speciality VARCHAR,country VARCHAR,postal_sector VARCHAR,active BOOLEAN", "hcp_id", {}, "one fictional professional"),
    "hco": ("hco_id VARCHAR,organisation_name VARCHAR,country VARCHAR", "hco_id", {}, "one fictional organisation"),
    "affiliation": ("affiliation_id VARCHAR,hcp_id VARCHAR,hco_id VARCHAR,relationship_type VARCHAR,is_primary BOOLEAN,effective_from DATE,effective_to DATE", "affiliation_id", {"hcp_id":"hcp.hcp_id","hco_id":"hco.hco_id"}, "one HCP–HCO relationship interval"),
    "product": ("product_id VARCHAR,product_name VARCHAR,active BOOLEAN", "product_id", {}, "one fictional marketed product"),
    "product_hierarchy": ("product_id VARCHAR,effective_from DATE,effective_to DATE,brand VARCHAR,therapy VARCHAR", "product_id,effective_from", {"product_id":"product.product_id"}, "one product hierarchy interval"),
    "territory": ("territory_id VARCHAR,territory_name VARCHAR", "territory_id", {}, "one territory"),
    "representative": ("rep_id VARCHAR,rep_name VARCHAR", "rep_id", {}, "one fictional representative"),
    "rep_territory": ("rep_id VARCHAR,territory_id VARCHAR,effective_from DATE,effective_to DATE", "rep_id,territory_id,effective_from", {"rep_id":"representative.rep_id","territory_id":"territory.territory_id"}, "one rep–territory interval"),
    "hcp_territory": ("assignment_id VARCHAR,hcp_id VARCHAR,territory_id VARCHAR,effective_from DATE,effective_to DATE", "assignment_id", {"hcp_id":"hcp.hcp_id","territory_id":"territory.territory_id"}, "one assignment interval; latest effective wins, equal-date conflict fails"),
    "interaction": ("interaction_id VARCHAR,version_no NUMBER,hcp_id VARCHAR,rep_id VARCHAR,primary_product_id VARCHAR,occurred_at TIMESTAMP_NTZ,channel VARCHAR,approval VARCHAR,duration_minutes NUMBER,modified_at TIMESTAMP_NTZ,operation VARCHAR,delivery_batch VARCHAR", "interaction_id,version_no", {"hcp_id":"hcp.hcp_id","rep_id":"representative.rep_id","primary_product_id":"product.product_id"}, "one interaction version, including tombstones"),
    "interaction_product": ("interaction_id VARCHAR,version_no NUMBER,product_id VARCHAR,detail_rank NUMBER", "interaction_id,version_no,product_id", {"product_id":"product.product_id"}, "one product per interaction version; complete detail replacement"),
    "consent_event": ("consent_id VARCHAR,hcp_id VARCHAR,channel VARCHAR,purpose VARCHAR,status VARCHAR,effective_at TIMESTAMP_NTZ,sequence_no NUMBER,delivery_batch VARCHAR", "consent_id", {"hcp_id":"hcp.hcp_id"}, "one preference event for HCP/channel/purpose"),
    "campaign": ("campaign_id VARCHAR,product_id VARCHAR,start_date DATE,end_date_exclusive DATE,status VARCHAR", "campaign_id", {"product_id":"product.product_id"}, "one single-product campaign"),
    "campaign_member": ("membership_id VARCHAR,campaign_id VARCHAR,hcp_id VARCHAR,member_status VARCHAR", "membership_id", {"campaign_id":"campaign.campaign_id","hcp_id":"hcp.hcp_id"}, "one campaign membership; campaign/HCP unique"),
    "rx_sales": ("observation_id VARCHAR,version_no NUMBER,hcp_id VARCHAR,product_id VARCHAR,week_ending DATE,trx_count NUMBER,nrx_count NUMBER,sales_units NUMBER", "observation_id,version_no", {"hcp_id":"hcp.hcp_id","product_id":"product.product_id"}, "one weekly HCP/product commercial observation version; no patient data"),
    "source_identity": ("entity_type VARCHAR,canonical_id VARCHAR,source VARCHAR,source_id VARCHAR,link_token VARCHAR", "entity_type,source,source_id", {}, "one hidden canonical-to-source identity; crawl IDs never reused")
}

def definitions():
    out = {}
    for name, (fields, pk, fk, grain) in MODEL.items():
        cols = []
        for f in fields.split(","):
            col, typ = f.split(" ", 1)
            cols.append({"name":col,"type":typ,"nullable":col in {"effective_to"}})
        out[name] = {"columns":cols,"primary_key":pk.split(","),"foreign_keys":fk,"grain":grain}
    out["interaction_product"]["composite_foreign_keys"] = [{"columns":["interaction_id","version_no"],"references":"interaction","reference_columns":["interaction_id","version_no"]}]
    out["source_identity"]["polymorphic_reference"] = "entity_type selects hcp, hco, product, territory, representative, interaction or campaign; canonical_id references its primary entity ID"
    return out

def export():
    write_json(ROOT/"contracts/canonical-model.json", definitions())
    sql = ["-- Run only as the evaluator in a private database. Never grant this schema to the builder.",
           "CREATE SCHEMA IF NOT EXISTS SYNTH_TRUTH;", "USE SCHEMA SYNTH_TRUTH;"]
    for name, definition in definitions().items():
        fields = [f"  {c['name']} {c['type']}" + (" NOT NULL" if not c["nullable"] else "") for c in definition["columns"]]
        fields += ["  PRIMARY KEY (" + ", ".join(definition["primary_key"]) + ")"]
        for col, ref in definition["foreign_keys"].items():
            table, refcol = ref.split(".")
            fields += [f"  FOREIGN KEY ({col}) REFERENCES {table} ({refcol})"]
        if name == "interaction_product":
            fields += ["  FOREIGN KEY (interaction_id, version_no) REFERENCES interaction (interaction_id, version_no)"]
        sql += [f"CREATE TABLE IF NOT EXISTS {name} (\n" + ",\n".join(fields) + "\n);"]
    (ROOT/"sql/00_canonical_private.sql").write_text("\n\n".join(sql)+"\n")

if __name__ == "__main__":
    export()
