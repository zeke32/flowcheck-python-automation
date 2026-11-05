#!/usr/bin/env python3
"""Portfolio demo: auditable CSV validation and reporting with the Python standard library."""
from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
FIELDS = ["order_id", "order_date", "customer_id", "region", "category", "units", "unit_price", "status"]
REGIONS = {"North", "South", "East", "West", "Central"}
STATUSES = {"completed", "pending", "cancelled"}


def validate(row: dict[str, str], seen: set[str]) -> tuple[dict | None, str | None]:
    missing = [field for field in FIELDS if not str(row.get(field, "")).strip()]
    if missing:
        return None, "Missing required field(s): " + ", ".join(missing)
    order_id = row["order_id"].strip()
    if order_id in seen:
        return None, "Duplicate order ID"
    try:
        order_date = date.fromisoformat(row["order_date"].strip())
    except ValueError:
        return None, "Invalid date (expected YYYY-MM-DD)"
    if row["region"].strip() not in REGIONS:
        return None, "Unknown region"
    status = row["status"].strip().lower()
    if status not in STATUSES:
        return None, "Unknown status"
    try:
        units = int(row["units"].strip())
        price = Decimal(row["unit_price"].strip())
        if units <= 0 or not price.is_finite() or price < 0:
            return None, "Units must be positive and unit price must be non-negative"
    except (ValueError, InvalidOperation):
        return None, "Invalid units or unit price"
    seen.add(order_id)
    return {
        "order_id": order_id,
        "order_date": order_date.isoformat(),
        "customer_id": row["customer_id"].strip(),
        "region": row["region"].strip(),
        "category": row["category"].strip(),
        "units": units,
        "unit_price": f"{price:.2f}",
        "status": status,
        "line_total": f"{(price * units):.2f}",
    }, None


def process(input_path: Path) -> tuple[list[dict], list[dict], dict]:
    accepted, rejected, seen = [], [], set()
    with input_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(field not in reader.fieldnames for field in FIELDS):
            raise ValueError("CSV must contain the required columns: " + ", ".join(FIELDS))
        for source_line, row in enumerate(reader, start=2):
            valid, issue = validate(row, seen)
            if issue:
                rejected.append({"source_line": source_line, "order_id": row.get("order_id", ""), "reason": issue})
            else:
                accepted.append(valid)
    revenue = sum((Decimal(record["line_total"]) for record in accepted if record["status"] == "completed"), Decimal("0"))
    revenue_by_region = defaultdict(lambda: Decimal("0"))
    revenue_by_category = defaultdict(lambda: Decimal("0"))
    for record in accepted:
        if record["status"] == "completed":
            amount = Decimal(record["line_total"])
            revenue_by_region[record["region"]] += amount
            revenue_by_category[record["category"]] += amount
    totals = Counter(record["status"] for record in accepted)
    issue_counts = Counter(record["reason"] for record in rejected)
    summary = {
        "input_rows": len(accepted) + len(rejected),
        "accepted_rows": len(accepted),
        "rejected_rows": len(rejected),
        "acceptance_pct": round(100 * len(accepted) / max(len(accepted) + len(rejected), 1), 1),
        "completed_orders": totals["completed"],
        "pending_orders": totals["pending"],
        "cancelled_orders": totals["cancelled"],
        "completed_revenue_usd": f"{revenue:.2f}",
        "revenue_by_region": {key: f"{val:.2f}" for key, val in sorted(revenue_by_region.items(), key=lambda pair: pair[1], reverse=True)},
        "revenue_by_category": {key: f"{val:.2f}" for key, val in sorted(revenue_by_category.items(), key=lambda pair: pair[1], reverse=True)},
        "issue_counts": dict(issue_counts),
    }
    return accepted, rejected, summary


def render_report(summary: dict, rejected: list[dict], template_path: Path) -> str:
    esc = html.escape
    fmt_money = lambda amount: "$" + f"{Decimal(amount):,.2f}"
    max_revenue = max((Decimal(v) for v in summary["revenue_by_region"].values()), default=Decimal("0"))
    chart_rows = []
    for region, value in summary["revenue_by_region"].items():
        percent = 100 * Decimal(value) / max_revenue if max_revenue else 0
        chart_rows.append(f'<div class="bar-row"><span>{esc(region)}</span><div class="track"><div class="fill" style="width:{float(percent):.1f}%"></div></div><strong>{fmt_money(value)}</strong></div>')
    issue_rows = []
    for reason, count in sorted(summary["issue_counts"].items(), key=lambda item: item[1], reverse=True):
        issue_rows.append(f'<div class="issue"><span>{esc(reason)}</span><strong>{count}</strong></div>')
    rejected_rows = []
    for record in rejected[:6]:
        rejected_rows.append(f'<tr><td>Line {record["source_line"]}</td><td>{esc(record["order_id"] or "(missing)")}</td><td>{esc(record["reason"])}</td></tr>')
    data = {
        "scanned": f'{summary["input_rows"]:,}',
        "accepted": f'{summary["accepted_rows"]:,}',
        "rejected": f'{summary["rejected_rows"]:,}',
        "revenue": fmt_money(summary["completed_revenue_usd"]),
        "quality": str(summary["acceptance_pct"]),
        "completed": str(summary["completed_orders"]),
        "pending": str(summary["pending_orders"]),
        "cancelled": str(summary["cancelled_orders"]),
        "bars": "".join(chart_rows) or '<p class="empty">No completed orders found.</p>',
        "issues": "".join(issue_rows) or '<p class="empty">No validation issues found.</p>',
        "rejected_rows": "".join(rejected_rows) or '<tr><td colspan="3">All rows passed validation.</td></tr>',
        "generated_at": datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC"),
    }
    return Template(template_path.read_text(encoding="utf-8")).substitute(data)


def run(input_path: Path, out_dir: Path) -> dict:
    accepted, rejected, summary = process(input_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "clean_orders.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS + ["line_total"])
        writer.writeheader()
        writer.writerows(accepted)
    with (out_dir / "rejected_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_line", "order_id", "reason"])
        writer.writeheader()
        writer.writerows(rejected)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.html").write_text(render_report(summary, rejected, ROOT / "assets" / "report_template.html"), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate business order CSV files and generate a self-contained HTML report.")
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "sample_orders.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "demo_output")
    args = parser.parse_args()
    summary = run(args.input, args.out)
    print(f'Processed {summary["input_rows"]} rows: {summary["accepted_rows"]} valid, {summary["rejected_rows"]} rejected.')
    print(f'Completed order revenue: $' + f'{summary["completed_revenue_usd"]}. Report: {args.out / "report.html"}')


if __name__ == "__main__":
    main()
