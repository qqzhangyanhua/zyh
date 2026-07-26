"""End-to-end tests for Issue #5: language rules, CI expansion, ecosystem_hypotheses."""

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


class ManifestLanguageTests(unittest.TestCase):
    def _scan(self, repo: Path) -> dict:
        result = run_script(str(SCAN), str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))

    def test_ruby_gemfile_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Gemfile").write_text("source 'https://rubygems.org'\n", encoding="utf-8")
            (repo / "Gemfile.lock").write_text("GEM\n  remote: https://rubygems.org/\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("Gemfile", facts["manifests"])
            self.assertIn("Gemfile.lock", facts["manifests"])

    def test_php_composer_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "composer.json").write_text('{"require": {}}\n', encoding="utf-8")
            (repo / "composer.lock").write_text('{"packages": []}\n', encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("composer.json", facts["manifests"])
            self.assertIn("composer.lock", facts["manifests"])

    def test_elixir_mix_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "mix.exs").write_text("defmodule App.MixProject do\nend\n", encoding="utf-8")
            (repo / "mix.lock").write_text("%{}\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("mix.exs", facts["manifests"])
            self.assertIn("mix.lock", facts["manifests"])

    def test_cpp_cmakelists_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.15)\n", encoding="utf-8")
            (repo / "conanfile.txt").write_text("[requires]\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("CMakeLists.txt", facts["manifests"])
            self.assertIn("conanfile.txt", facts["manifests"])

    def test_bazel_build_workspace_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "BUILD").write_text('cc_binary(name = "app")\n', encoding="utf-8")
            (repo / "WORKSPACE").write_text('workspace(name = "myapp")\n', encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("BUILD", facts["manifests"])
            self.assertIn("WORKSPACE", facts["manifests"])

    def test_asdf_tool_versions_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".tool-versions").write_text("python 3.11.0\nnode 20.0.0\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn(".tool-versions", facts["manifests"])


class CIConfigExpansionTests(unittest.TestCase):
    def _scan(self, repo: Path) -> dict:
        result = run_script(str(SCAN), str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))

    def test_bitbucket_pipelines_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "bitbucket-pipelines.yml").write_text("pipelines:\n  default:\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("bitbucket-pipelines.yml", facts["ci_configs"])

    def test_drone_ci_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".drone.yml").write_text("kind: pipeline\nname: default\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn(".drone.yml", facts["ci_configs"])

    def test_woodpecker_ci_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".woodpecker.yml").write_text("pipeline:\n  build:\n    image: golang\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn(".woodpecker.yml", facts["ci_configs"])


class TestFileExpansionTests(unittest.TestCase):
    def _scan(self, repo: Path) -> dict:
        result = run_script(str(SCAN), str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))

    def test_conftest_py_detected_as_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "conftest.py").write_text("import pytest\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("src/conftest.py", facts["test_files"])

    def test_conftest_py_at_root_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "conftest.py").write_text("import pytest\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("conftest.py", facts["test_files"])

    def test_go_test_file_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pkg").mkdir()
            (repo / "pkg" / "service_test.go").write_text("package pkg\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("pkg/service_test.go", facts["test_files"])


class GeneratedFileExpansionTests(unittest.TestCase):
    def _scan(self, repo: Path) -> dict:
        result = run_script(str(SCAN), str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))

    def test_gen_go_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "api").mkdir()
            (repo / "api" / "types.gen.go").write_text("package api\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("api/types.gen.go", facts["generated_candidates"])

    def test_pb2_py_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "proto").mkdir()
            (repo / "proto" / "service_pb2.py").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("proto/service_pb2.py", facts["generated_candidates"])

    def test_dts_file_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "dist").mkdir()
            # dist is a SKIP_DIR, use a non-skipped dir
            (repo / "types").mkdir()
            (repo / "types" / "index.d.ts").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("types/index.d.ts", facts["generated_candidates"])

    def test_generated_dir_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src" / "__generated__").mkdir(parents=True)
            (repo / "src" / "__generated__" / "schema.ts").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("src/__generated__/schema.ts", facts["generated_candidates"])


class RiskKeywordExpansionTests(unittest.TestCase):
    def _scan(self, repo: Path) -> dict:
        result = run_script(str(SCAN), str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))

    def _risk_reasons(self, facts: dict) -> list[str]:
        return [r["reason"] for r in facts["risk_candidates"]]

    def test_iam_risk_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "iam").mkdir()
            (repo / "iam" / "policy.py").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("IAM or access control", self._risk_reasons(facts))

    def test_rbac_risk_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "rbac_check.py").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("role-based access control", self._risk_reasons(facts))

    def test_terraform_risk_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "terraform").mkdir()
            (repo / "terraform" / "main.tf").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("infrastructure-as-code (Terraform)", self._risk_reasons(facts))

    def test_helm_risk_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "helm").mkdir()
            (repo / "helm" / "values.yaml").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("Helm chart or Kubernetes package", self._risk_reasons(facts))

    def test_stripe_risk_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "stripe_webhook.py").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("payment processing (Stripe)", self._risk_reasons(facts))

    def test_pii_risk_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "pii_handler.py").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("personally identifiable information", self._risk_reasons(facts))


class EcosystemHypothesesTests(unittest.TestCase):
    def _scan(self, repo: Path) -> dict:
        result = run_script(str(SCAN), str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))

    def _ecosystems(self, facts: dict) -> list[str]:
        return [h["ecosystem"] for h in facts["ecosystem_hypotheses"]]

    def test_node_hypothesis_from_package_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text('{"name": "app"}\n', encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("node", self._ecosystems(facts))

    def test_python_hypothesis_from_pyproject(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text("[project]\nname = 'app'\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("python", self._ecosystems(facts))

    def test_rust_hypothesis_from_cargo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Cargo.toml").write_text("[package]\nname = \"app\"\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("rust", self._ecosystems(facts))

    def test_multiple_ecosystems_in_monorepo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text('{"name": "frontend"}\n', encoding="utf-8")
            (repo / "pyproject.toml").write_text("[project]\nname = 'backend'\n", encoding="utf-8")
            facts = self._scan(repo)
            ecosystems = self._ecosystems(facts)
            self.assertIn("node", ecosystems)
            self.assertIn("python", ecosystems)

    def test_hypothesis_has_evidence_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "go.mod").write_text("module example.com/app\n\ngo 1.21\n", encoding="utf-8")
            facts = self._scan(repo)
            go_hyp = next((h for h in facts["ecosystem_hypotheses"] if h["ecosystem"] == "go"), None)
            self.assertIsNotNone(go_hyp)
            self.assertIn("go.mod", go_hyp["evidence"])
            self.assertIn("hint", go_hyp)

    def test_no_hypotheses_for_empty_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "README.md").write_text("# Hello\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertEqual(facts["ecosystem_hypotheses"], [])

    def test_ruby_hypothesis_from_gemfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Gemfile").write_text("source 'https://rubygems.org'\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("ruby", self._ecosystems(facts))


if __name__ == "__main__":
    unittest.main()
