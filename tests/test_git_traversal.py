"""Tests for git ls-files traversal and submodule/ignored_top_dirs (Slice 1)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_tests_dir = str(Path(__file__).resolve().parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)
from helpers import SCAN, init_git_repo, run_git, run_script


class GitTraversalTests(unittest.TestCase):
    def test_scan_git_repo_uses_git_ls_files_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            init_git_repo(repo)
            (repo / ".gitignore").write_text("vendor/\n.agent/\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "vendor").mkdir()
            (repo / "src" / "auth.py").write_text("", encoding="utf-8")
            (repo / "package.json").write_text(json.dumps({"scripts": {}}), encoding="utf-8")
            (repo / "vendor" / "api.generated.ts").write_text("", encoding="utf-8")
            expected = run_git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--deduplicate")
            self.assertEqual(expected.returncode, 0, expected.stderr)
            expected_files = sorted(item for item in expected.stdout.split("\0") if item)

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertEqual(facts["scanned_file_count"], len(expected_files))
            self.assertIn("package.json", facts["manifests"])
            self.assertTrue(any(item["path"] == "src/auth.py" for item in facts["risk_candidates"]))
            self.assertNotIn("vendor/api.generated.ts", facts["generated_candidates"])

    def test_scan_non_git_repo_uses_expanded_skip_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("", encoding="utf-8")
            skipped_dirs = [
                "vendor", "third_party", "target", "out", "coverage",
                ".tox", ".pytest_cache", ".mypy_cache", "bazel-bin", ".gradle",
                ".idea", ".vscode",
            ]
            for dirname in skipped_dirs:
                (repo / dirname).mkdir()
                (repo / dirname / "auth_generated_test.py").write_text("", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            all_candidates = (
                facts["test_files"]
                + facts["generated_candidates"]
                + [item["path"] for item in facts["risk_candidates"]]
                + [item["path"] for item in facts["important_flow_candidates"]]
            )
            for dirname in skipped_dirs:
                self.assertFalse(
                    any(path.startswith(f"{dirname}/") for path in all_candidates),
                    f"{dirname}/ must be skipped by non-git fallback traversal",
                )

    def test_scan_git_repo_records_ignored_top_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            init_git_repo(repo)
            (repo / ".gitignore").write_text("build-output/\n.agent/\n", encoding="utf-8")
            (repo / "build-output").mkdir()
            (repo / "build-output" / "artifact.txt").write_text("", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertEqual(facts["ignored_top_dirs"], ["build-output"])

    def test_scan_git_repo_records_submodules_without_scanning_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            submodule_source = Path(temp_dir) / "submodule-source"
            submodule_source.mkdir()
            init_git_repo(submodule_source)
            (submodule_source / "nested_auth.py").write_text("", encoding="utf-8")
            run_git(submodule_source, "add", "nested_auth.py")
            commit_submodule = run_git(submodule_source, "commit", "-m", "initial submodule")
            if commit_submodule.returncode != 0:
                raise unittest.SkipTest(f"git commit failed: {commit_submodule.stderr}")

            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            init_git_repo(repo)
            add_submodule = subprocess.run(
                ["git", "-c", "protocol.file.allow=always", "submodule", "add",
                 str(submodule_source), "vendor/submodule"],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )
            if add_submodule.returncode != 0:
                raise unittest.SkipTest(f"git submodule add failed: {add_submodule.stderr}")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertTrue(any(item["path"] == "vendor/submodule" for item in facts["submodules"]))
            self.assertFalse(
                any(item["path"].startswith("vendor/submodule/") for item in facts["risk_candidates"]),
                "main repo risk candidates must not include submodule internals",
            )


if __name__ == "__main__":
    unittest.main()
