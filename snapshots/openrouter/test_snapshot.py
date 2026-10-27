import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import snapshot  # noqa: E402

# Shape copied from a live /endpoints response on 2026-10-26, trimmed.
MODELS = [{"id": "openai/gpt-oss-120b", "created": 1754414231,
           "links": {"details": "/api/v1/models/openai/gpt-oss-120b/endpoints"}}]
ENDPOINTS = {
    "openai/gpt-oss-120b": {"data": {"name": "OpenAI: gpt-oss-120b", "endpoints": [
        {"name": "Near AI | openai/gpt-oss-120b", "model_name": "OpenAI: gpt-oss-120b",
         "provider_name": "Near AI", "tag": "near-ai/fp4", "quantization": "fp4",
         "context_length": 131072, "max_completion_tokens": 117964,
         "pricing": {"prompt": "0.00000003", "completion": "0.00000015",
                     "input_cache_read": "0.000000015", "discount": 0},
         "supported_parameters": ["reasoning", "tools"], "status": 0,
         "uptime_last_1d": 99.65277777777779, "latency_last_30m": None},
        {"name": "Other | openai/gpt-oss-120b", "provider_name": "Other",
         "tag": "other", "quantization": None,
         "pricing": {"prompt": "0.0000001", "completion": "0.0000005",
                     "request": "0.001", "image": "0"},
         "supported_parameters": []},
    ]}}
}


class TestNormalize(unittest.TestCase):
    def setUp(self):
        self.rows = snapshot.normalize("2026-10-26", "2026-10-26T06:17:00+00:00",
                                       MODELS, ENDPOINTS)

    def test_one_row_per_endpoint_with_all_columns(self):
        self.assertEqual(len(self.rows), 2)
        for r in self.rows:
            self.assertEqual(list(r), snapshot.CSV_COLUMNS)

    def test_prices_exact_per_million(self):
        r = self.rows[0]
        self.assertEqual(r["usd_per_m_prompt"], "0.03")
        self.assertEqual(r["usd_per_m_completion"], "0.15")
        self.assertEqual(r["usd_per_m_input_cache_read"], "0.015")
        self.assertEqual(r["usd_per_m_input_cache_write"], "")

    def test_non_token_pricing_kept_verbatim(self):
        r = self.rows[1]
        self.assertEqual(json.loads(r["pricing_other"]), {"image": "0", "request": "0.001"})
        self.assertEqual(self.rows[0]["pricing_other"], "")

    def test_metadata(self):
        r0, r1 = self.rows
        self.assertEqual(r0["quantization"], "fp4")
        self.assertEqual(r1["quantization"], "")
        self.assertTrue(r0["supports_tools"])
        self.assertFalse(r1["supports_tools"])
        self.assertTrue(r0["model_created_utc"].startswith("2025-08-05"))
        self.assertEqual(r1["model_name"], "OpenAI: gpt-oss-120b")

    def test_variant_flags(self):
        endpoints = dict(ENDPOINTS)
        base = ENDPOINTS["openai/gpt-oss-120b"]
        endpoints["openai/gpt-oss-120b:batch"] = base
        endpoints["openai/gpt-oss-120b:free"] = {"data": {"endpoints": base["data"]["endpoints"][:1]}}
        rows = snapshot.normalize("2026-10-26", "t", MODELS, endpoints)
        flags = {(r["model_id"], r["variant"], r["variant_same_as_base"]) for r in rows}
        self.assertIn(("openai/gpt-oss-120b", "", ""), flags)
        self.assertIn(("openai/gpt-oss-120b:batch", "batch", True), flags)
        self.assertIn(("openai/gpt-oss-120b:free", "free", False), flags)
        self.assertTrue(all(r["base_model_id"] == "openai/gpt-oss-120b" for r in rows))

    def test_per_m_edge_cases(self):
        self.assertEqual(snapshot.per_m("0"), "0")
        self.assertEqual(snapshot.per_m("-1"), "-1000000")  # OpenRouter uses -1 for "variable"
        self.assertEqual(snapshot.per_m(None), "")
        self.assertEqual(snapshot.per_m("n/a"), "")

    def test_endpoints_path(self):
        self.assertEqual(snapshot.endpoints_path(MODELS[0]),
                         "/models/openai/gpt-oss-120b/endpoints")
        self.assertEqual(snapshot.endpoints_path({"id": "a/b:free"}), "/models/a/b:free/endpoints")


if __name__ == "__main__":
    unittest.main()
