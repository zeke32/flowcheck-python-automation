"""Deterministic synthetic CSV dataset. No real customers or client data."""
from __future__ import annotations
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
rows = []
for i in range(240):
    day = date(2026, 7, 1) + timedelta(days=random.randint(0, 91))
    rows.append({
        "order_id": f"ORD-{10001+i}", "order_date": day.isoformat(), "customer_id": f"CUST-{random.randint(101,199)}",
        "region": random.choices(["North","South","East","West","Central"], weights=[25,20,20,18,17])[0],
        "category": random.choice(["Office","Home","Outdoor","Electronics"]), "units": str(random.randint(1, 8)),
        "unit_price": f"{random.choice([25.0, 39.5, 62.0, 79.0, 99.0, 149.0, 220.0]):.2f}",
        "status": random.choices(["completed","pending","cancelled"], weights=[78,14,8])[0],
    })
for i in range(4):
    invalid = dict(rows[i + 1]); invalid["order_id"] = rows[i]["order_id"]; rows.append(invalid)
for i in range(3):
    invalid = dict(rows[i + 12]); invalid["order_id"] = f"BAD-DATE-{i}"; invalid["order_date"] = "2026-88-12"; rows.append(invalid)
for i in range(2):
    invalid = dict(rows[i + 25]); invalid["order_id"] = f"BAD-QTY-{i}"; invalid["units"] = "0"; rows.append(invalid)
for i in range(2):
    invalid = dict(rows[i + 35]); invalid["order_id"] = f"BAD-PRICE-{i}"; invalid["unit_price"] = "-12.00"; rows.append(invalid)
for i in range(2):
    invalid = dict(rows[i + 45]); invalid["order_id"] = f"BAD-REGION-{i}"; invalid["region"] = "Outer Space"; rows.append(invalid)
for i in range(2):
    invalid = dict(rows[i + 55]); invalid["order_id"] = f"BAD-EMPTY-{i}"; invalid["customer_id"] = ""; rows.append(invalid)
path = Path(__file__).with_name("sample_orders.csv")
with path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
print(f"Generated {len(rows)} rows -> {path}")
