"""Regression tests for scan coverage, candidate totals, risk matching, and CI command extraction."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_tests_dir = str(Path(__file__).resolve().parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)
from helpers import ROOT, SCAN, init_git_repo, run_script

sys.path.insert(0, str(ROOT / "scripts"))
from harness.content_detectors import ContentBudget, extract_ci_commands
from harness.detectors import detect_ci_configs, detect_risks
from harness.scanner import scan as scanner_scan


def _touch(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _risk_paths(facts: dict) -> set[str]:
    return {item["path"] for item in facts["risk_candidates"]}


class ScanCoverageTests(unittest.TestCase):
    def _build_skewed_repo(self, repo: Path) -> None:
        for i in range(120):
            _touch(repo / "apps" / f"f{i:03d}.txt")
        _touch(repo / "src" / "auth" / "login.py")
        _touch(repo / "tests" / "test_a.py")

    def test_limit_samples_every_top_dir_in_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            self._build_skewed_repo(repo)
            facts = scanner_scan(repo, limit=50, deep=False)
            self.assertIn("src/auth/login.py", _risk_paths(facts))
            self.assertIn("tests/test_a.py", facts["test_files"])
            self.assertTrue(facts["truncated"])
            self.assertEqual(facts["truncation_strategy"]["mode"], "proportional")
            self.assertLessEqual(facts["scanned_file_count"], 50)

    def test_limit_samples_every_top_dir_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._build_skewed_repo(repo)
            facts = scanner_scan(repo, limit=50, deep=False)
            self.assertIn("src/auth/login.py", _risk_paths(facts))
            self.assertIn("tests/test_a.py", facts["test_files"])
            self.assertLessEqual(facts["scanned_file_count"], 50)

    def test_sampling_spreads_within_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for i in range(100):
                _touch(repo / "src" / f"a{i:03d}.py")
            _touch(repo / "src" / "zz_auth.py")
            facts = scanner_scan(repo, limit=20, deep=False)
            self.assertIn("src/zz_auth.py", _risk_paths(facts))
            self.assertLessEqual(facts["scanned_file_count"], 20)

    def test_force_over_max_threshold_still_samples_proportionally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for name in ("a", "b", "c"):
                for i in range(5):
                    _touch(repo / name / f"{name}_auth_{i}.py")
            facts = scanner_scan(repo, limit=6, deep=False, force=True, _max_threshold=0)
            self.assertEqual(facts["truncation_strategy"]["mode"], "proportional")
            tops = {path.split("/", 1)[0] for path in _risk_paths(facts)}
            self.assertEqual(tops, {"a", "b", "c"})

    def test_truncated_false_when_file_count_equals_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for i in range(3):
                _touch(repo / f"file{i}.txt")
            facts = scanner_scan(repo, limit=3, deep=False)
            self.assertFalse(facts["truncated"])
            self.assertEqual(facts["truncation_strategy"], {})

    def test_cli_default_limit_covers_full_scan_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _touch(repo / "README.md", "# x\n")
            result = run_script(str(SCAN), str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertEqual(facts["scan_limit"], 50_000)

    def test_git_root_files_grouped_under_dot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            _touch(repo / "README.md")
            _touch(repo / "src" / "main.py")
            facts = scanner_scan(repo, limit=5000, deep=False)
            self.assertEqual(facts["top_level_file_counts"], {".": 1, "src": 1})

    def test_git_scan_ignores_agent_output_even_when_not_gitignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            _touch(repo / ".agent" / "repo-facts.json", "{}")
            _touch(repo / ".agent" / "auth_generated_test.py")
            _touch(repo / "src" / "main.py")
            facts = scanner_scan(repo, limit=5000, deep=False)
            self.assertEqual(facts["total_files"], 1)
            self.assertEqual(facts["scanned_file_count"], 1)
            self.assertEqual(facts["risk_candidates"], [])

    def test_scan_falls_back_when_git_binary_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir()
            _touch(repo / "src" / "auth.py")
            with mock.patch("harness.walker.subprocess.run", side_effect=FileNotFoundError("git")):
                facts = scanner_scan(repo, limit=5000, deep=False)
            self.assertEqual(facts["total_files"], 1)
            self.assertIn("src/auth.py", _risk_paths(facts))


class CandidateTotalsTests(unittest.TestCase):
    def test_candidate_totals_are_not_capped_before_sampling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for i in range(700):
                _touch(repo / "tests" / f"test_{i:03d}.py")
            full_output = repo / "out" / "repo-facts.full.json"
            facts = scanner_scan(repo, limit=5000, deep=False, full_output=full_output)
            self.assertEqual(facts["test_files_total"], 700)
            self.assertTrue(facts["test_files_truncated"])
            self.assertEqual(len(facts["test_files"]), 500)
            full = json.loads(full_output.read_text(encoding="utf-8"))
            self.assertEqual(len(full["test_files"]), 700)

    def test_makefile_totals_reflect_parser_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _touch(repo / "Makefile", "\n".join(f"target{i}:\n\techo {i}" for i in range(250)))
            full_output = repo / "out" / "repo-facts.full.json"
            facts = scanner_scan(repo, limit=5000, deep=False, full_output=full_output)
            self.assertEqual(facts["makefile_targets_total"], 250)
            self.assertTrue(facts["makefile_targets_truncated"])
            self.assertEqual(len(facts["makefile_targets"]), 200)
            full = json.loads(full_output.read_text(encoding="utf-8"))
            self.assertEqual(len(full["makefile_targets"]), 250)


class RiskMatchingTests(unittest.TestCase):
    def _reasons_by_path(self, *paths: str) -> dict[str, set[str]]:
        root = Path("/repo")
        result: dict[str, set[str]] = {}
        for item in detect_risks([root / p for p in paths], root):
            result.setdefault(item["path"], set()).add(item["reason"])
        return result

    def test_path_can_carry_multiple_risk_reasons(self) -> None:
        reasons = self._reasons_by_path("db/migrations/auth_users.sql")
        self.assertEqual(
            reasons["db/migrations/auth_users.sql"],
            {"auth or authentication", "database migrations"},
        )

    def test_substring_false_positives_are_not_flagged(self) -> None:
        reasons = self._reasons_by_path(
            "src/williams_diagram.py", "docs/author.md", "ui/prototype.tsx", "docs/overwhelm.md"
        )
        self.assertEqual(reasons, {})

    def test_camel_case_and_prefix_tokens_are_flagged(self) -> None:
        reasons = self._reasons_by_path(
            "src/router/AuthGuard.tsx", "src/IAMPolicy.ts", "src/secretsManager.ts", "ops/deployer.sh"
        )
        self.assertIn("auth or authentication", reasons["src/router/AuthGuard.tsx"])
        self.assertIn("IAM or access control", reasons["src/IAMPolicy.ts"])
        self.assertIn("secrets", reasons["src/secretsManager.ts"])
        self.assertIn("deployment", reasons["ops/deployer.sh"])


class CiExtractionTests(unittest.TestCase):
    def _commands(self, repo: Path, rel_path: str, content: str) -> list[dict]:
        _touch(repo / rel_path, content)
        return extract_ci_commands([rel_path], repo, ContentBudget(8 * 1024 * 1024), [])

    def test_gitlab_script_lists_are_extracted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._commands(
                Path(tmp),
                ".gitlab-ci.yml",
                "test:\n  before_script:\n  - pip install -e .\n  script:\n    - make test\n    - \"pytest -q\"\n  artifacts:\n    paths:\n      - dist/\n",
            )
            commands = [c["command"] for c in result]
            self.assertEqual(commands, ["pip install -e .", "make test", "pytest -q"])

    def test_gitlab_single_line_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._commands(Path(tmp), ".gitlab-ci.yml", "test:\n  script: pytest\n")
            self.assertEqual([c["command"] for c in result], ["pytest"])

    def test_circleci_run_command_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._commands(
                Path(tmp),
                ".circleci/config.yml",
                "jobs:\n  t:\n    steps:\n      - run:\n          name: unit\n          command: npm test\n"
                "      - run:\n          command: |\n            npm ci\n            npm run build\n",
            )
            self.assertEqual([c["command"] for c in result], ["npm test", "npm ci"])
            self.assertEqual([c["multiline"] for c in result], [False, True])

    def test_github_script_action_body_is_not_a_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._commands(
                Path(tmp),
                ".github/workflows/ci.yml",
                "jobs:\n  t:\n    steps:\n      - uses: actions/github-script@v7\n        with:\n          script: |\n            console.log(1)\n",
            )
            self.assertEqual(result, [])

    def test_github_dir_only_counts_workflow_and_action_yaml(self) -> None:
        root = Path("/repo")
        paths = [
            ".github/workflows/ci.yml",
            ".github/actions/setup/action.yml",
            ".github/CODEOWNERS",
            ".github/ISSUE_TEMPLATE/bug.md",
            ".github/dependabot.yml",
            ".gitlab/issue_templates/bug.md",
            ".gitlab/ci/test.yml",
        ]
        hits = detect_ci_configs([root / p for p in paths], root)
        self.assertEqual(
            sorted(hits),
            [".github/actions/setup/action.yml", ".github/workflows/ci.yml", ".gitlab/ci/test.yml"],
        )


if __name__ == "__main__":
    unittest.main()
