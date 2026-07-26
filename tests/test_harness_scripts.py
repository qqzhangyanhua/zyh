from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_tests_dir = str(Path(__file__).resolve().parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)
from helpers import SCAN, run_script


class HarnessScriptTests(unittest.TestCase):
    def test_scan_repo_writes_v2_schema_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertEqual(facts["schema_version"], 2)
            self.assertEqual(facts["total_files"], 0)
            self.assertEqual(facts["top_level_file_counts"], {})
            self.assertEqual(facts["ignored_top_dirs"], [])
            self.assertEqual(facts["submodules"], [])
            self.assertEqual(facts["truncation_strategy"], {})
            self.assertEqual(facts["suggested_shards"], [])
            self.assertEqual(facts["ecosystem_hypotheses"], [])
            self.assertEqual(facts["command_provenance_index"], [])
            self.assertEqual(facts["ci_commands"], [])
            self.assertEqual(facts["dockerfile_directives"], [])
            self.assertEqual(facts["tool_configs"], {})
            self.assertEqual(facts["env_keys"], [])
            self.assertEqual(facts["precommit_hooks_detail"], [])
            self.assertEqual(facts["codeowners"], [])
            self.assertEqual(facts["parse_errors"], [])
            self.assertEqual(facts["content_read_truncated"], [])

            candidate_fields = (
                "test_files",
                "generated_candidates",
                "risk_candidates",
                "important_flow_candidates",
                "docs",
                "ci_configs",
                "makefile_targets",
                "doc_hints",
            )
            for field in candidate_fields:
                self.assertEqual(facts[f"{field}_total"], 0)
                self.assertFalse(facts[f"{field}_truncated"])

    def test_scan_cli_keeps_existing_options(self) -> None:
        result = run_script(str(SCAN), "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("repo", result.stdout)
        self.assertIn("--limit", result.stdout)
        self.assertIn("--deep", result.stdout)
        self.assertIn("--output", result.stdout)

    def test_scan_repo_writes_conservative_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "backend" / "auth").mkdir(parents=True)
            (repo / "generated").mkdir()
            (repo / "package.json").write_text(
                json.dumps({"scripts": {"lint": "eslint .", "test": "vitest"}}),
                encoding="utf-8",
            )
            (repo / "backend" / "auth" / "test_login.py").write_text("", encoding="utf-8")
            (repo / "generated" / "api.generated.ts").write_text("", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertIn("backend", facts["top_level"]["directories"])
            self.assertIn("package.json", facts["manifests"])
            self.assertEqual(facts["package_commands"]["test"], "vitest")
            self.assertEqual(facts["package_scripts"]["package.json"], ["lint", "test"])
            self.assertTrue(
                any(item["reason"] == "auth or authentication" for item in facts["risk_candidates"])
            )
            self.assertIn("generated/api.generated.ts", facts["generated_candidates"])

    def test_deep_scan_collects_doc_hints_and_missing_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "src" / "router").mkdir(parents=True)
            (repo / "src" / "router" / "AuthGuard.tsx").write_text("", encoding="utf-8")
            (repo / "README.md").write_text(
                "\n".join(
                    [
                        "# App",
                        "Use pnpm type-check before commit.",
                        "The router handles auth and permission checks.",
                    ]
                ),
                encoding="utf-8",
            )
            (repo / "package.json").write_text(
                json.dumps({"scripts": {"type-check": "tsc --noEmit"}}),
                encoding="utf-8",
            )

            result = run_script(str(SCAN), "--deep", "--limit", "20000", str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertEqual(facts["scan_mode"], "deep")
            self.assertIn("README.md", facts["docs"])
            self.assertIn("No package.json lint script detected.", facts["missing_capabilities"])
            self.assertIn("No dedicated test runner or test files detected.", facts["missing_capabilities"])
            self.assertTrue(any(item["path"] == "README.md" for item in facts["doc_hints"]))
            self.assertTrue(
                any(item["purpose"] == "route guard or auth guard" for item in facts["important_flow_candidates"])
            )

    def test_scan_detects_ci_configs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / ".github" / "workflows").mkdir(parents=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
            (repo / ".gitlab-ci.yml").write_text("test:\n  script: pytest\n", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertTrue(any(".github" in p for p in facts["ci_configs"]))
            self.assertIn(".gitlab-ci.yml", facts["ci_configs"])

    def test_scan_skips_agent_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / ".agent").mkdir()
            (repo / ".agent" / "repo-facts.json").write_text("{}", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            all_files = (
                facts.get("test_files", [])
                + facts.get("generated_candidates", [])
                + facts.get("risk_candidates", [])
            )
            self.assertFalse(
                any(".agent" in str(f) for f in all_files),
                ".agent/ contents must not appear in scan results",
            )

    def test_scan_detects_bin_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "bin").mkdir()
            (repo / "bin" / "build.sh").write_text("#!/usr/bin/env sh\necho build\n", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertIn("bin/build.sh", facts["existing_scripts"])

    def test_scan_includes_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertIn("scan_timestamp", facts)
            self.assertRegex(facts["scan_timestamp"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_scan_detects_makefile_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "Makefile").write_text(
                "build:\n\tgo build ./...\ntest:\n\tgo test ./...\nlint:\n\tgolangci-lint run\n",
                encoding="utf-8",
            )

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertIn("build", facts["makefile_targets"])
            self.assertIn("test", facts["makefile_targets"])
            self.assertIn("lint", facts["makefile_targets"])

    def test_scan_detects_precommit_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertIn(".pre-commit-config.yaml", facts["precommit_hooks"])

    def test_scan_non_js_repo_skips_package_json_lint_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")

            result = run_script(str(SCAN), "--deep", str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertNotIn(
                "No package.json lint script detected.",
                facts["missing_capabilities"],
                "non-JS repos must not report a missing package.json lint script",
            )

    def test_scan_detects_python_config_and_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            (repo / "ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertIn("pytest.ini", facts["configs"])
            self.assertIn("ruff.toml", facts["configs"])
            self.assertTrue(
                any(item["purpose"] == "Python app entrypoint" for item in facts["important_flow_candidates"]),
                "main.py should be detected as a Python app entrypoint",
            )

    def test_scan_detects_monorepo_workspace_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n", encoding="utf-8")
            (repo / "turbo.json").write_text("{}\n", encoding="utf-8")

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertIn("pnpm-workspace.yaml", facts["manifests"])
            self.assertIn("turbo.json", facts["manifests"])

    def test_scan_detects_package_scripts_under_skip_named_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "build" / "repo"
            repo.mkdir(parents=True)
            (repo / "package.json").write_text(
                json.dumps({"scripts": {"test": "vitest", "lint": "eslint"}}),
                encoding="utf-8",
            )

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertEqual(facts["package_scripts"].get("package.json"), ["lint", "test"])

    def test_scan_detects_nested_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "scripts" / "ci").mkdir(parents=True)
            (repo / "scripts" / "ci" / "checks.sh").write_text(
                "#!/usr/bin/env sh\nset -eu\n", encoding="utf-8"
            )

            result = run_script(str(SCAN), str(repo))

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertIn("scripts/ci/checks.sh", facts["existing_scripts"])

    def test_scan_reports_truncated_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            for i in range(5):
                (repo / f"file{i}.txt").write_text("", encoding="utf-8")

            limited = run_script(str(SCAN), "--limit", "2", str(repo))
            self.assertEqual(limited.returncode, 0, limited.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertTrue(facts["truncated"])

            full = run_script(str(SCAN), str(repo))
            self.assertEqual(full.returncode, 0, full.stderr)
            facts = json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))
            self.assertFalse(facts["truncated"])


if __name__ == "__main__":
    unittest.main()
