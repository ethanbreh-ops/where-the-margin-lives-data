import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scrape_leaderboard as sl  # noqa: E402

# Record shape seen in the live page on 2026-10-27, trimmed.
ITEMS = [{"modelId": "m__text", "modelName": "M", "release": {"date": "2025-04-14"},
          "agentVersion": "text", "meta": {"developer": "d", "instance_type": "model"},
          "rangeStats": {"all": {
              "1735689600000:1736899200000": {"resolvedRate": 31.3, "sem": 1.47, "passN": 43.5,
                                              "instanceCosts": 0, "totalTokenUsage": 0,
                                              "cachedTokenPercentage": None},
              "1779494400000:1782864000000": {"resolvedRate": 64.5, "sem": 1.41, "passN": 70.0,
                                              "instanceCosts": 4.4, "totalTokenUsage": 2518308.09,
                                              "cachedTokenPercentage": 94.93}}}}]


def page(items):
    body = '{"x":1,"items":' + json.dumps(items) + "}"
    chunk = json.dumps(body)[1:-1]  # escaped as it appears inside the push() string
    return f'<script>self.__next_f.push([1,"{chunk}"])</script>'


class TestScrape(unittest.TestCase):
    def test_round_trip(self):
        items = sl.extract_items(sl.payload(page(ITEMS)))
        self.assertEqual(items[0]["modelId"], "m__text")

    def test_rows(self):
        r = sl.rows(ITEMS, "2026-10-27")
        self.assertEqual(len(r), 2)
        old, new = sorted(r, key=lambda x: x["window_from"])
        self.assertEqual((old["window_from"], old["window_to"]), ("2025-01-01", "2025-01-15"))
        self.assertEqual(old["cost_per_problem_usd"], "")   # site's 0 means no data
        self.assertEqual(old["cached_token_pct"], "")
        self.assertEqual(new["cost_per_problem_usd"], 4.4)
        self.assertEqual(new["cached_token_pct"], 94.93)

    def test_missing_items_raises(self):
        with self.assertRaises(ValueError):
            sl.extract_items("nothing here")


if __name__ == "__main__":
    unittest.main()
