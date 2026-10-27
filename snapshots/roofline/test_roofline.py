import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import roofline as rf  # noqa: E402

H200 = {"hbm_tb_s": 4.8, "bf16_dense_tflops": 989.5, "fp8_dense_tflops": 1979}


class TestParamCounts(unittest.TestCase):
    """Derived counts must match the totals the model publishers state."""

    def test_gpt_oss_120b(self):
        m = rf.load_model(rf.CONFIGS / "gpt-oss-120b.config.json")
        self.assertAlmostEqual(rf.total_params(m) / 1e9, 117, delta=2)   # model card: 117B
        self.assertAlmostEqual(m.active_params / 1e9, 5.1, delta=0.2)    # model card: 5.1B active

    def test_deepseek_r1(self):
        m = rf.load_model(rf.CONFIGS / "DeepSeek-R1-0528.config.json")
        self.assertAlmostEqual(rf.total_params(m) / 1e9, 671, delta=10)  # 671B (excl. MTP layer)
        self.assertAlmostEqual(m.active_params / 1e9, 37, delta=1.5)     # 37B active


class TestCeiling(unittest.TestCase):
    def setUp(self):
        self.m = rf.load_model(rf.CONFIGS / "DeepSeek-R1-0528.config.json")

    def test_min_routing_is_the_higher_ceiling(self):
        lo = rf.ceiling(self.m, H200, 8, 8192, 1024, 64, "fp8", "uniform")
        hi = rf.ceiling(self.m, H200, 8, 8192, 1024, 64, "fp8", "min")
        self.assertGreater(hi["output_tput_per_gpu"], lo["output_tput_per_gpu"])

    def test_single_stream_is_memory_bound_at_weight_read_speed(self):
        # conc=1: one token per step, step time ~ active weight bytes / (8 x 4.8 TB/s)
        r = rf.ceiling(self.m, H200, 8, 1, 1, 1, "fp8", "min")
        self.assertEqual(r["decode_bound"], "memory")
        expected = 8 * 4.8e12 / (self.m.active_params * 1.0)  # ~1,000 tok/s
        self.assertAlmostEqual(r["interactivity_tok_s_user"] / expected, 1, delta=0.05)

    def test_throughput_rises_with_concurrency(self):
        a = rf.ceiling(self.m, H200, 8, 1024, 1024, 4, "fp8")["output_tput_per_gpu"]
        b = rf.ceiling(self.m, H200, 8, 1024, 1024, 64, "fp8")["output_tput_per_gpu"]
        self.assertGreater(b, a)


if __name__ == "__main__":
    unittest.main()
