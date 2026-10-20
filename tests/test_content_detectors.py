"""Tests for Issue #7: content-layer detectors (CI/Dockerfile/pyproject tools/env/precommit/CODEOWNERS) + content budget."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_tests_dir = str(Path(__file__).resolve().parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)
sys.path.insert(0, str(_root / "scripts"))

from harness.content_detectors import (
    ContentBudget,
    extract_ci_commands,
    extract_codeowners,
    extract_dockerfile_directives,
    extract_env_keys,
    extract_precommit_hooks_detail,
    extract_security_md,
    extract_tool_configs,
)
from helpers import SCAN, run_script


class CiCommandsTests(unittest.TestCase):
    def test_single_line_run_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".github" / "workflows").mkdir(parents=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(
                "name: CI\non: [push]\njobs:\n  test:\n    steps:\n      - run: pytest -q\n      - run: echo done\n",
                encoding="utf-8",
            )
            truncated: list[dict] = []
            result = extract_ci_commands(
                [".github/workflows/ci.yml"], repo, ContentBudget(8 * 1024 * 1024), truncated
            )
            commands = [c["command"] for c in result]
            self.assertIn("pytest -q", commands)
            self.assertIn("echo done", commands)
            self.assertTrue(all(c["source"] == "ci_workflow" for c in result))
            self.assertTrue(all(c["multiline"] is False for c in result))
            self.assertEqual(truncated, [])

    def test_multiline_block_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".github" / "workflows").mkdir(parents=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(
                "jobs:\n  test:\n    steps:\n      - run: |\n          set -e\n          pytest -q\n",
                encoding="utf-8",
            )
            truncated: list[dict] = []
            result = extract_ci_commands(
                [".github/workflows/ci.yml"], repo, ContentBudget(8 * 1024 * 1024), truncated
            )
            self.assertEqual(len(result), 1)
            self.assertTrue(result[0]["multiline"])
            self.assertEqual(result[0]["command"], "set -e")

    def test_workflow_field_uses_file_stem(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".gitlab-ci.yml").write_text("test:\n  script:\n    - run: make test\n", encoding="utf-8")
            truncated: list[dict] = []
            result = extract_ci_commands([".gitlab-ci.yml"], repo, ContentBudget(8 * 1024 * 1024), truncated)
            self.assertTrue(any(c["workflow"] == ".gitlab-ci" for c in result))


class DockerfileDirectivesTests(unittest.TestCase):
    def test_directives_covered(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Dockerfile").write_text(
                "\n".join(
                    [
                        "FROM python:3.11",
                        "WORKDIR /app",
                        "RUN pip install -r requirements.txt",
                        "USER appuser",
                        "EXPOSE 8080",
                        "ENTRYPOINT [\"python\", \"main.py\"]",
                        "CMD [\"--serve\"]",
                    ]
                ),
                encoding="utf-8",
            )
            truncated: list[dict] = []
            result = extract_dockerfile_directives(
                [repo / "Dockerfile"], repo, ContentBudget(8 * 1024 * 1024), truncated
            )
            directives = {d["directive"] for d in result}
            self.assertEqual(directives, {"WORKDIR", "RUN", "USER", "EXPOSE", "ENTRYPOINT", "CMD"})
            self.assertEqual(truncated, [])

    def test_prefixed_dockerfile_name_matched(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "backend.Dockerfile").write_text("RUN echo hi\n", encoding="utf-8")
            truncated: list[dict] = []
            result = extract_dockerfile_directives(
                [repo / "backend.Dockerfile"], repo, ContentBudget(8 * 1024 * 1024), truncated
            )
            self.assertEqual(len(result), 1)


class ToolConfigsTests(unittest.TestCase):
    def test_pytest_ruff_mypy_top_level_keys_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[tool.pytest.ini_options]",
                        'testpaths = ["tests"]',
                        "addopts = '-ra'",
                        "[tool.ruff]",
                        "line-length = 100",
                        "select = ['E', 'F']",
                        "[tool.mypy]",
                        "strict = true",
                    ]
                ),
                encoding="utf-8",
            )
            errors: list[dict] = []
            truncated: list[dict] = []
            result = extract_tool_configs(repo, ContentBudget(8 * 1024 * 1024), truncated, errors)
            self.assertEqual(sorted(result["pytest.ini_options"]), ["addopts", "testpaths"])
            self.assertEqual(sorted(result["ruff"]), ["line-length", "select"])
            self.assertEqual(sorted(result["mypy"]), ["strict"])
            self.assertEqual(errors, [])

    def test_malformed_toml_populates_parse_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text("[[invalid\nbroken\n", encoding="utf-8")
            errors: list[dict] = []
            truncated: list[dict] = []
            result = extract_tool_configs(repo, ContentBudget(8 * 1024 * 1024), truncated, errors)
            self.assertEqual(result, {})
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["kind"], "toml_parse")

    def test_no_pyproject_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors: list[dict] = []
            truncated: list[dict] = []
            result = extract_tool_configs(Path(tmp), ContentBudget(8 * 1024 * 1024), truncated, errors)
            self.assertEqual(result, {})


class EnvKeysTests(unittest.TestCase):
    def test_example_file_keys_extracted_without_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".env.example").write_text("API_KEY=changeme\nDATABASE_URL=postgres://x\n", encoding="utf-8")
            errors: list[dict] = []
            truncated: list[dict] = []
            result = extract_env_keys([repo / ".env.example"], repo, ContentBudget(8 * 1024 * 1024), truncated, errors)
            keys = [e["key"] for e in result]
            self.assertIn("API_KEY", keys)
            self.assertIn("DATABASE_URL", keys)
            dump = json.dumps(result)
            self.assertNotIn("changeme", dump)
            self.assertNotIn("postgres://x", dump)
            self.assertEqual(errors, [])

    def test_real_dotenv_skipped_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".env").write_text("SECRET=topsecret\n", encoding="utf-8")
            errors: list[dict] = []
            truncated: list[dict] = []
            result = extract_env_keys([repo / ".env"], repo, ContentBudget(8 * 1024 * 1024), truncated, errors)
            self.assertEqual(result, [])
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["kind"], "skipped_dotenv")
            self.assertNotIn("topsecret", json.dumps(errors))

    def test_sample_and_template_suffixes_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".env.SAMPLE").write_text("FOO=bar\n", encoding="utf-8")
            (repo / ".env.template").write_text("BAZ=qux\n", encoding="utf-8")
            errors: list[dict] = []
            truncated: list[dict] = []
            files = [repo / ".env.SAMPLE", repo / ".env.template"]
            result = extract_env_keys(files, repo, ContentBudget(8 * 1024 * 1024), truncated, errors)
            keys = [e["key"] for e in result]
            self.assertIn("FOO", keys)
            self.assertIn("BAZ", keys)
            self.assertEqual(errors, [])


class PrecommitHooksDetailTests(unittest.TestCase):
    def test_hook_ids_covered(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".pre-commit-config.yaml").write_text(
                "\n".join(
                    [
                        "repos:",
                        "  - repo: https://github.com/psf/black",
                        "    rev: 23.1.0",
                        "    hooks:",
                        "      - id: black",
                        "  - repo: local",
                        "    hooks:",
                        "      - id: mypy",
                        "      - id: flake8",
                    ]
                ),
                encoding="utf-8",
            )
            truncated: list[dict] = []
            result = extract_precommit_hooks_detail(repo, ContentBudget(8 * 1024 * 1024), truncated)
            ids = {h["hook_id"] for h in result}
            self.assertEqual(ids, {"black", "mypy", "flake8"})
            black_entry = next(h for h in result if h["hook_id"] == "black")
            self.assertEqual(black_entry["repo"], "https://github.com/psf/black")

    def test_no_config_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            truncated: list[dict] = []
            result = extract_precommit_hooks_detail(Path(tmp), ContentBudget(8 * 1024 * 1024), truncated)
            self.assertEqual(result, [])


class CodeownersTests(unittest.TestCase):
    def test_entries_and_owners_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "CODEOWNERS").write_text(
                "# comment\n*.py @alice\n/docs/ @bob @carol\n\n/infra/ @deploy-team\n",
                encoding="utf-8",
            )
            truncated: list[dict] = []
            result = extract_codeowners(repo, ContentBudget(8 * 1024 * 1024), truncated)
            by_pattern = {e["pattern"]: e["owners"] for e in result}
            self.assertEqual(by_pattern["*.py"], ["@alice"])
            self.assertEqual(by_pattern["/docs/"], ["@bob", "@carol"])
            self.assertEqual(by_pattern["/infra/"], ["@deploy-team"])

    def test_github_subdir_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".github").mkdir()
            (repo / ".github" / "CODEOWNERS").write_text("* @root-owner\n", encoding="utf-8")
            truncated: list[dict] = []
            result = extract_codeowners(repo, ContentBudget(8 * 1024 * 1024), truncated)
            self.assertEqual(result[0]["pattern"], "*")


class SecurityMdTests(unittest.TestCase):
    def test_summary_first_200_chars_whitespace_collapsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            body = "Please   report\n\nvulnerabilities   to security@example.com." + ("x" * 300)
            (repo / "SECURITY.md").write_text(body, encoding="utf-8")
            truncated: list[dict] = []
            result = extract_security_md(repo, ContentBudget(8 * 1024 * 1024), truncated)
            self.assertEqual(result["path"], "SECURITY.md")
            self.assertLessEqual(len(result["summary"]), 200)
            self.assertNotIn("  ", result["summary"])

    def test_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            truncated: list[dict] = []
            result = extract_security_md(Path(tmp), ContentBudget(8 * 1024 * 1024), truncated)
            self.assertIsNone(result)


class ContentBudgetTests(unittest.TestCase):
    def test_oversized_file_truncated_and_scan_still_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Dockerfile").write_text("RUN " + ("x" * 5000) + "\n", encoding="utf-8")
            truncated: list[dict] = []
            budget = ContentBudget(10)
            result = extract_dockerfile_directives([repo / "Dockerfile"], repo, budget, truncated)
            self.assertEqual(result, [])
            self.assertEqual(len(truncated), 1)
            self.assertEqual(truncated[0]["reason"], "budget_exceeded")
            self.assertEqual(truncated[0]["kind"], "dockerfile")

    def test_budget_shared_across_detectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Dockerfile").write_text("RUN echo one\n", encoding="utf-8")
            (repo / "CODEOWNERS").write_text("* @owner\n", encoding="utf-8")
            truncated: list[dict] = []
            budget = ContentBudget(5)
            dockerfile_result = extract_dockerfile_directives([repo / "Dockerfile"], repo, budget, truncated)
            codeowners_result = extract_codeowners(repo, budget, truncated)
            self.assertEqual(dockerfile_result, [])
            self.assertEqual(codeowners_result, [])
            self.assertEqual(len(truncated), 2)


class EndToEndContentLayerTests(unittest.TestCase):
    def _scan(self, repo: Path, *extra: str) -> dict:
        result = run_script(str(SCAN), *extra, str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))

    def test_all_new_fields_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            for field in (
                "ci_commands",
                "dockerfile_directives",
                "tool_configs",
                "env_keys",
                "precommit_hooks_detail",
                "codeowners",
                "security_md",
                "content_read_truncated",
                "content_budget_bytes",
            ):
                self.assertIn(field, facts, f"missing {field}")

    def test_full_content_layer_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".github" / "workflows").mkdir(parents=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(
                "jobs:\n  test:\n    steps:\n      - run: pytest -q\n", encoding="utf-8"
            )
            (repo / "Dockerfile").write_text("RUN pip install -r requirements.txt\n", encoding="utf-8")
            (repo / "pyproject.toml").write_text(
                "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
            )
            (repo / ".env.example").write_text("API_KEY=changeme\n", encoding="utf-8")
            (repo / ".env").write_text("API_KEY=realsecret\n", encoding="utf-8")
            (repo / ".pre-commit-config.yaml").write_text(
                "repos:\n  - repo: local\n    hooks:\n      - id: black\n", encoding="utf-8"
            )
            (repo / "CODEOWNERS").write_text("* @team\n", encoding="utf-8")
            (repo / "SECURITY.md").write_text("Report issues to security@example.com.\n", encoding="utf-8")

            facts = self._scan(repo)

            self.assertTrue(any(c["command"] == "pytest -q" for c in facts["ci_commands"]))
            self.assertTrue(any(d["directive"] == "RUN" for d in facts["dockerfile_directives"]))
            self.assertIn("ruff", facts["tool_configs"])
            env_keys = [e["key"] for e in facts["env_keys"]]
            self.assertIn("API_KEY", env_keys)
            self.assertEqual(json.dumps(facts["env_keys"]).count("realsecret"), 0)
            self.assertTrue(any(e["kind"] == "skipped_dotenv" for e in facts["parse_errors"]))
            self.assertTrue(any(h["hook_id"] == "black" for h in facts["precommit_hooks_detail"]))
            self.assertEqual(facts["codeowners"][0]["pattern"], "*")
            self.assertIsNotNone(facts["security_md"])
            self.assertEqual(facts["security_md"]["path"], "SECURITY.md")

    def test_content_budget_bytes_cli_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Dockerfile").write_text("RUN " + ("x" * 2000) + "\n", encoding="utf-8")
            facts = self._scan(repo, "--content-budget-bytes", "5")
            self.assertEqual(facts["dockerfile_directives"], [])
            self.assertTrue(any(t["kind"] == "dockerfile" for t in facts["content_read_truncated"]))

    def test_readme_command_blocks_not_read_by_content_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "README.md").write_text("```sh\npnpm test\n```\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertEqual(facts["ci_commands"], [])

    def test_slice0_to_4_fields_still_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Makefile").write_text("build:\n\techo hi\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertEqual(facts["schema_version"], 2)
            for field in ("makefile_targets", "makefile_phony_targets", "cargo_workspace_members", "total_files"):
                self.assertIn(field, facts)


if __name__ == "__main__":
    unittest.main()
