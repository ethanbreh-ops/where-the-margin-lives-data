import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import extract_trajectories as ex  # noqa: E402

# Message shapes observed in real trajectories on 2026-10-27, trimmed.
ANTHROPIC = {"role": "assistant", "extra": {"cost": 0.01, "timestamp": 100.0, "response": {
    "model": "claude-opus-4-6", "usage": {
        "prompt_tokens": 1000, "completion_tokens": 50,
        "completion_tokens_details": {"reasoning_tokens": 10},
        "prompt_tokens_details": {"cached_tokens": 0, "cache_creation_tokens": 0},
        "cache_read_input_tokens": 900, "cache_creation_input_tokens": 80}}}}
OPENROUTER = {"role": "assistant", "extra": {"cost": 0.002, "timestamp": 130.5, "response": {
    "model": "z-ai/glm-5", "provider": "Z.AI", "usage": {
        "prompt_tokens": 1485, "completion_tokens": 270,
        "prompt_tokens_details": {"cached_tokens": 192},
        "completion_tokens_details": {"reasoning_tokens": 200}}}}}
OPENAI_RESPONSES = {"object": "response", "model": "gpt-5.2-2025-12-11",
                    "usage": {"input_tokens": 1359, "output_tokens": 304,
                              "input_tokens_details": {"cached_tokens": 0},
                              "output_tokens_details": {"reasoning_tokens": 100}},
                    "extra": {"cost": 0.0066, "timestamp": 200.0}}
GEMINI = {"role": "assistant", "extra": {"cost": 0.003, "response": {
    "model": "gemini-3-pro", "usage": {
        "prompt_tokens": 1510, "completion_tokens": 82,
        "completion_tokens_details": {"reasoning_tokens": 66},
        "prompt_tokens_details": {"cached_tokens": None}, "cache_read_input_tokens": None}}}}
TOOL = {"role": "tool", "extra": {"returncode": 0, "raw_output": "ok"}}


class TestCallUsage(unittest.TestCase):
    def test_non_calls_skipped(self):
        self.assertIsNone(ex.call_usage(TOOL))
        self.assertIsNone(ex.call_usage({"role": "user", "content": "hi"}))

    def test_anthropic_cache_fields(self):
        c = ex.call_usage(ANTHROPIC)
        self.assertEqual((c["input"], c["cache_read"], c["cache_write"], c["output"], c["reasoning"]),
                         (1000, 900, 80, 50, 10))

    def test_openrouter_cached_tokens_fallback(self):
        c = ex.call_usage(OPENROUTER)
        self.assertEqual((c["cache_read"], c["cache_write"], c["provider"]), (192, None, "Z.AI"))

    def test_openai_responses_format(self):
        c = ex.call_usage(OPENAI_RESPONSES)
        self.assertEqual((c["input"], c["output"], c["cache_read"], c["reasoning"], c["model"]),
                         (1359, 304, 0, 100, "gpt-5.2-2025-12-11"))

    def test_unreported_cache_stays_none(self):
        self.assertIsNone(ex.call_usage(GEMINI)["cache_read"])


class TestParseTrajectory(unittest.TestCase):
    def test_sums_and_cost_check(self):
        traj = {"messages": [ANTHROPIC, TOOL, ANTHROPIC], "info": {"exit_status": "Submitted"}}
        inst, rows = ex.parse_trajectory("sub", "i1", traj, {"cost": 0.02, "resolved": True}, "e", 9)
        self.assertEqual(len(rows), 2)
        self.assertEqual(inst["input_tokens"], 2000)
        self.assertEqual(inst["cache_read_tokens"], 1800)
        self.assertTrue(inst["cost_matches"])
        self.assertEqual(inst["token_classes_missing"], "")
        self.assertEqual(rows[1]["call_idx"], 1)

    def test_missing_classes_flagged_and_cost_mismatch(self):
        traj = {"messages": [GEMINI], "info": {}}
        inst, rows = ex.parse_trajectory("sub", "i2", traj, {"cost": 0.5}, "e", 1)
        self.assertIn("cache_read", inst["token_classes_missing"])
        self.assertFalse(inst["cost_matches"])
        self.assertEqual(rows[0]["cache_read_tokens"], "")


class TestMetadata(unittest.TestCase):
    def test_parse(self):
        text = ("info:\n  name: Claude 4.6 Opus\n  mini-swe-agent_version: 2.0.0\n  resolved: 75.6\n"
                "  cost: 275.7\n  instance_cost: 0.55\n  instance_calls: 28.9\n"
                "  model_release_date: 20260205\ntags:\n  model:\n  - claude-opus-4-6\n"
                "  org: Anthropic\n  os_model: false\n  model_display: Claude 4.6 Opus\n"
                "  model_org: Anthropic\n")
        m = ex.parse_metadata(text)
        self.assertEqual(m["model_ids"], "claude-opus-4-6")
        self.assertEqual(m["mini_version"], "2.0.0")
        self.assertEqual(m["resolved_pct_reported"], "75.6")
        self.assertEqual(m["model_org"], "Anthropic")


if __name__ == "__main__":
    unittest.main()
