"""File interchange only. No transformation logic shared by reference and oracle."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def write_csv(path, rows, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

GOLD_COLUMNS = {
    "s01_engagement": ["activity_key", "customer_key", "activity_date", "consent_status"],
    "s02_product_activity": ["customer_key", "product_code", "activity_date", "brand", "therapy", "interaction_count"],
    "s03_customer_territory": ["customer_key", "territory_code", "assignment_status"],
    "s04_interaction": ["activity_key", "customer_key", "primary_product_code", "occurred_at", "channel", "duration_minutes", "source_version"],
    "s05_campaign": ["campaign_key", "customer_key", "product_code", "contacted", "qualifying_interactions"],
    "exceptions": ["scenario", "record_key", "reason"],
    "dq": ["scenario", "scope", "numerator", "denominator", "threshold", "status"]
}

def write_results(folder, outputs):
    for name, cols in GOLD_COLUMNS.items():
        rows = outputs.get(name, [])
        rows = sorted(rows, key=lambda r: tuple(str(r.get(c, "")) for c in cols))
        write_csv(Path(folder) / (name + ".csv"), rows, cols)
