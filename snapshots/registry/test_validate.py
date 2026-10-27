import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import validate  # noqa: E402

GOOD = {
    "source_id": "X-1", "source": "Example", "url": "https://example.com",
    "effective_date": "FY2025", "access_date": "2026-10-27", "metric": "m", "units": "u",
    "model_or_workload": "w", "status": "observed", "source_tier": "primary",
    "caveats": "list price only", "snapshot_path": "data/a.csv (note; with semicolon)",
}


class TestValidate(unittest.TestCase):
    def run_rows(self, rows, files=("data/a.csv",)):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for f in files:
                (root / f).parent.mkdir(parents=True, exist_ok=True)
                (root / f).write_text("x")
            reg = root / "sources.csv"
            with open(reg, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=validate.COLUMNS)
                w.writeheader()
                w.writerows(rows)
            return validate.validate(reg, root)

    def test_valid_row(self):
        self.assertEqual(self.run_rows([GOOD]), [])

    def test_bad_values_reported(self):
        bad = dict(GOOD, source_id="x 1", status="observed (audited)", source_tier="blog",
                   access_date="yesterday", caveats="none", url="example.com")
        errs = " ".join(self.run_rows([bad]))
        for word in ("source_id", "status", "source_tier", "access_date", "caveats", "url"):
            self.assertIn(word, errs)

    def test_duplicate_and_missing_snapshot(self):
        errs = self.run_rows([GOOD, dict(GOOD, snapshot_path="data/<date>/missing.csv")])
        self.assertTrue(any("duplicate" in e for e in errs))
        self.assertTrue(any("matches no file" in e for e in errs))

    def test_date_wildcard(self):
        row = dict(GOOD, snapshot_path="data/raw/<date>/m.json.gz")
        self.assertEqual(self.run_rows([row], files=("data/raw/2026-10-27/m.json.gz",)), [])


if __name__ == "__main__":
    unittest.main()
