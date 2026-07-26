"""Integration tests for Issue #4: two-phase scan, metadata fields, --full/--force."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_tests_dir = str(Path(__file__).resolve().parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)
from helpers import ROOT, SCAN, run_script

sys.path.insert(0, str(ROOT / "scripts"))
from harness.scanner import FileLimitError
from harness.scanner import scan as scanner_scan


class ScannerSlicesTests(unittest.TestCase):
    def test_total_files_and_top_level_counts_populated(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("", encoding="utf-8")
            (repo / "src" / "util.py").write_text("", encoding="utf-8")
            (repo / "tests").mkdir()
            (repo / "tests" / "test_main.py").write_text("", encoding="utf-8")
            result = run_script(str(SCAN), str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text())
            self.assertEqual(facts["total_files"], 3)
            self.assertIn("src", facts["top_level_file_counts"])
            self.assertIn("tests", facts["top_level_file_counts"])

    def test_candidate_fields_have_total_and_truncated_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "auth.py").write_text("", encoding="utf-8")
            result = run_script(str(SCAN), str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text())
            for field in (
                "test_files", "generated_candidates", "risk_candidates",
                "important_flow_candidates", "docs", "ci_configs", "makefile_targets",
            ):
                self.assertIn(f"{field}_total", facts, f"missing {field}_total")
                self.assertIn(f"{field}_truncated", facts, f"missing {field}_truncated")

    def test_full_flag_writes_full_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "README.md").write_text("# Test", encoding="utf-8")
            result = run_script(str(SCAN), "--full", str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((repo / ".agent" / "repo-facts.json").exists())
            self.assertTrue((repo / ".agent" / "repo-facts.full.json").exists())

    def test_full_json_has_valid_schema_and_unrestricted_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("", encoding="utf-8")
            run_script(str(SCAN), "--full", str(repo))
            full = json.loads((repo / ".agent" / "repo-facts.full.json").read_text())
            self.assertEqual(full["schema_version"], 2)
            self.assertFalse(full["test_files_truncated"])
            self.assertFalse(full["generated_candidates_truncated"])
            self.assertFalse(full["risk_candidates_truncated"])
            self.assertFalse(full["important_flow_candidates_truncated"])

    def test_force_flag_accepted_by_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "file.txt").write_text("x", encoding="utf-8")
            result = run_script(str(SCAN), "--force", str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_file_limit_error_raised_when_over_max_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "file.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(FileLimitError) as ctx:
                scanner_scan(repo, limit=5000, deep=False, _max_threshold=0)
            self.assertGreater(ctx.exception.total, 0)
            self.assertEqual(ctx.exception.threshold, 0)

    def test_force_overrides_file_limit_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "file.txt").write_text("x", encoding="utf-8")
            facts = scanner_scan(repo, limit=5000, deep=False, force=True, _max_threshold=0)
            self.assertGreater(facts["total_files"], 0)

    def test_proportional_mode_triggered_over_full_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "a").mkdir()
            (repo / "a" / "file.txt").write_text("x", encoding="utf-8")
            (repo / "b").mkdir()
            (repo / "b" / "file.txt").write_text("x", encoding="utf-8")
            facts = scanner_scan(repo, limit=5000, deep=False, _full_threshold=1, _max_threshold=500_000)
            self.assertEqual(facts["truncation_strategy"]["mode"], "proportional")
            self.assertIn("a", facts["suggested_shards"])
            self.assertIn("b", facts["suggested_shards"])

    def test_standard_mode_for_small_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "file.txt").write_text("x", encoding="utf-8")
            facts = scanner_scan(repo, limit=5000, deep=False)
            self.assertEqual(facts["truncation_strategy"], {})
            self.assertEqual(facts["suggested_shards"], [])


if __name__ == "__main__":
    unittest.main()
