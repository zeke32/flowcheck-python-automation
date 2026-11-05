import csv
import tempfile
import unittest
from pathlib import Path
from app import process, run, validate

BASE = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(order_id="O-1", order_date="2026-10-01", customer_id="C-1", region="North", category="Office", units="2", unit_price="10.25", status="completed")

    def test_valid_row_and_decimal_total(self):
        record, issue = validate(self.row, set())
        self.assertIsNone(issue)
        self.assertEqual(record["line_total"], "20.50")

    def test_duplicate_order(self):
        seen = set()
        validate(self.row, seen)
        _, issue = validate(self.row, seen)
        self.assertEqual(issue, "Duplicate order ID")

    def test_invalid_units_and_negative_price(self):
        for field, value in [("units", "0"), ("unit_price", "-1")]:
            with self.subTest(field=field):
                row = self.row | {field: value}
                self.assertIsNotNone(validate(row, set())[1])

    def test_invalid_date(self):
        self.assertEqual(validate(self.row | {"order_date": "yesterday"}, set())[1], "Invalid date (expected YYYY-MM-DD)")

    def test_missing_field(self):
        self.assertIn("Missing required", validate(self.row | {"customer_id": ""}, set())[1])

    def test_complete_run_and_files(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            summary = run(BASE / "data" / "sample_orders.csv", out)
            self.assertEqual(summary["input_rows"], 255)
            self.assertEqual(summary["rejected_rows"], 15)
            self.assertEqual(summary["accepted_rows"], 240)
            self.assertEqual(summary["accepted_rows"] + summary["rejected_rows"], summary["input_rows"])
            self.assertTrue((out / "report.html").exists())
            self.assertIn("Synthetic data only", (out / "report.html").read_text())
            with (out / "clean_orders.csv").open() as f:
                self.assertEqual(len(list(csv.DictReader(f))), 240)

    def test_missing_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("id,price\n1,20\n")
            with self.assertRaisesRegex(ValueError, "required columns"):
                process(path)


if __name__ == "__main__":
    unittest.main()
