"""Unit tests for harness.sampling.sample_with_buckets."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "scripts"))
from harness.sampling import sample_with_buckets


class SampleWithBucketsTests(unittest.TestCase):
    def test_no_truncation_when_under_cap(self):
        items = list(range(5))
        result, total, truncated = sample_with_buckets(items, 10, str)
        self.assertEqual(result, items)
        self.assertEqual(total, 5)
        self.assertFalse(truncated)

    def test_exact_cap_not_truncated(self):
        items = list(range(5))
        result, total, truncated = sample_with_buckets(items, 5, str)
        self.assertEqual(result, items)
        self.assertEqual(total, 5)
        self.assertFalse(truncated)

    def test_empty_input(self):
        result, total, truncated = sample_with_buckets([], 10, str)
        self.assertEqual(result, [])
        self.assertEqual(total, 0)
        self.assertFalse(truncated)

    def test_single_bucket_capped(self):
        items = [f"a/{i}.py" for i in range(20)]
        result, total, truncated = sample_with_buckets(items, 5, lambda p: p.split("/")[0])
        self.assertEqual(len(result), 5)
        self.assertEqual(total, 20)
        self.assertTrue(truncated)
        self.assertEqual(result, items[:5])

    def test_proportional_across_buckets(self):
        items = [f"a/{i}" for i in range(60)] + [f"b/{i}" for i in range(40)]
        result, total, truncated = sample_with_buckets(items, 10, lambda p: p.split("/")[0])
        self.assertEqual(total, 100)
        self.assertTrue(truncated)
        self.assertEqual(len(result), 10)
        n_a = sum(1 for x in result if x.startswith("a/"))
        n_b = sum(1 for x in result if x.startswith("b/"))
        self.assertGreater(n_a, n_b)

    def test_preserves_order_within_bucket(self):
        items = [f"src/{i}.py" for i in range(10)]
        result, _, _ = sample_with_buckets(items, 5, lambda p: p.split("/")[0])
        self.assertEqual(result, items[:5])

    def test_fewer_slots_than_buckets(self):
        items = ["c/x", "b/x", "a/x"]
        result, total, truncated = sample_with_buckets(items, 2, lambda p: p.split("/")[0])
        self.assertEqual(total, 3)
        self.assertTrue(truncated)
        self.assertEqual(len(result), 2)
        self.assertIn("a/x", result)
        self.assertIn("b/x", result)

    def test_returns_total_as_original_length(self):
        items = [f"x/{i}" for i in range(100)]
        _, total, _ = sample_with_buckets(items, 10, lambda p: p.split("/")[0])
        self.assertEqual(total, 100)

    def test_result_length_equals_cap_when_truncated(self):
        items = [f"dir/{i}" for i in range(1000)]
        result, _, truncated = sample_with_buckets(items, 500, lambda p: p.split("/")[0])
        self.assertTrue(truncated)
        self.assertEqual(len(result), 500)


if __name__ == "__main__":
    unittest.main()
