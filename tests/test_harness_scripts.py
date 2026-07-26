from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_repo.py"
VALIDATE = ROOT / "scripts" / "validate_harness_docs.py"


def run_script(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def require_git() -> None:
    result = subprocess.run(
        ["git", "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise unittest.SkipTest("git is required for scanner traversal tests")


def init_git_repo(repo: Path) -> None:
    require_git()
    self_result = run_git(repo, "init")
    if self_result.returncode != 0:
        raise unittest.SkipTest(f"git init failed: {self_result.stderr}")
    run_git(repo, "config", "user.email", "agent@example.com")
    run_git(repo, "config", "user.name", "Agent Test")


def write_minimal_harness(repo: Path, check_body: str, *, executable: bool = True) -> None:
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "scripts").mkdir(exist_ok=True)
    (repo / "AGENTS.md").write_text(
        "\n".join(
            [
                "# Agent Instructions",
                "- docs/project-map.md",
                "- docs/testing.md",
                "- docs/dangerous-areas.md",
                "- docs/debugging.md",
                "- docs/agent-plan-template.md",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "docs/project-map.md").write_text("# Project Map\n\nTODO: map repo.\n", encoding="utf-8")
    (repo / "docs/testing.md").write_text("# Testing\n\nTODO: verify commands.\n", encoding="utf-8")
    (repo / "docs/dangerous-areas.md").write_text(
        "\n".join(
            [
                "# Dangerous Areas",
                "- auth",
                "- permission",
                "- billing",
                "- migration",
                "- infra",
                "- secret",
                "- generated",
                "- public api",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "docs/debugging.md").write_text("# Debugging\n\nTODO: add known failures.\n", encoding="utf-8")
    (repo / "docs/agent-plan-template.md").write_text("# Agent Plan\n\nTODO\n", encoding="utf-8")
    check_sh = repo / "scripts/check.sh"
    check_sh.write_text(check_body, encoding="utf-8")
    if executable:
        check_sh.chmod(0o755)


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

    def test_validate_cli_keeps_existing_interface(self) -> None:
        result = run_script(str(VALIDATE), "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("repo", result.stdout)

    def test_validate_rejects_v1_repo_facts_with_rescan_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / ".agent").mkdir()
            (repo / ".agent" / "repo-facts.json").write_text(
                json.dumps({"root": str(repo), "top_level": {}}),
                encoding="utf-8",
            )

            result = run_script(str(VALIDATE), str(repo))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "repo-facts.json is schema v1 and no longer supported. "
                "Re-run: python3 scripts/scan_repo.py <repo-root>",
                result.stdout,
            )
            self.assertNotIn("missing required file", result.stdout)

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
                "vendor",
                "third_party",
                "target",
                "out",
                "coverage",
                ".tox",
                ".pytest_cache",
                ".mypy_cache",
                "bazel-bin",
                ".gradle",
                ".idea",
                ".vscode",
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
                [
                    "git",
                    "-c",
                    "protocol.file.allow=always",
                    "submodule",
                    "add",
                    str(submodule_source),
                    "vendor/submodule",
                ],
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

    def test_validate_accepts_harness_with_todo_and_verified_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "scripts").mkdir()
            (repo / "scripts/test.sh").write_text("#!/usr/bin/env sh\nset -eu\n", encoding="utf-8")
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n./scripts/test.sh\n")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("harness docs validated", result.stdout)

    def test_validate_rejects_unverified_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\npnpm test\n")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("unverified command: pnpm test", result.stdout)

    def test_validate_rejects_runtime_command_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(
                repo,
                "\n".join(
                    [
                        "#!/usr/bin/env sh",
                        "set -eu",
                        "if command -v pytest >/dev/null 2>&1; then",
                        "  pytest",
                        "fi",
                    ]
                ),
            )

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("runtime command guessing: command -v pytest", result.stdout)

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

    @unittest.skipIf(sys.platform == "win32", "Windows does not support Unix executable bits")
    def test_validate_rejects_non_executable_check_sh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n", executable=False)

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("not executable", result.stdout)

    def test_validate_dangerous_areas_skips_absent_risk_terms(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            # No auth/billing/migration paths — repo-facts will have no risk_candidates
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")
            # Override dangerous-areas with only generic content (no risk terms)
            (repo / "docs/dangerous-areas.md").write_text(
                "# Dangerous Areas\n\nNo high-risk areas detected.\n", encoding="utf-8"
            )

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validate_rejects_missing_script_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n./scripts/nonexistent.sh\n")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("references missing script", result.stdout)

    def test_validate_rejects_missing_script_reference_no_dotslash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\nbin/missing.sh\n")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("references missing script", result.stdout)

    def test_validate_rejects_unknown_in_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")
            (repo / "docs/testing.md").write_text(
                "# Testing\n\nUnknown: test runner not found.\n", encoding="utf-8"
            )

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("Unknown", result.stdout)

    def test_validate_rejects_agents_md_too_long(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")
            long_agents = "\n".join(
                ["# Agent Instructions"]
                + ["- docs/project-map.md", "- docs/testing.md", "- docs/dangerous-areas.md",
                   "- docs/debugging.md", "- docs/agent-plan-template.md"]
                + [f"# Section {i}\n\nPadding line.\n" for i in range(40)]
            )
            (repo / "AGENTS.md").write_text(long_agents, encoding="utf-8")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("too long", result.stdout)

    def test_validate_rejects_missing_required_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")
            (repo / "docs/dangerous-areas.md").unlink()

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("missing required file: docs/dangerous-areas.md", result.stdout)

    def test_validate_accepts_bin_script_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "bin").mkdir()
            (repo / "bin" / "test.sh").write_text("#!/usr/bin/env sh\nset -eu\n", encoding="utf-8")
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n./bin/test.sh\n")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
            # Repo lives under a parent directory named like a SKIP_DIR ("build").
            # package_scripts must not be skipped based on the absolute path.
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

    def test_validate_accepts_nested_script_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "scripts" / "ci").mkdir(parents=True)
            (repo / "scripts" / "ci" / "checks.sh").write_text(
                "#!/usr/bin/env sh\nset -eu\n", encoding="utf-8"
            )
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n./scripts/ci/checks.sh\n")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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

    def test_validate_requires_payments_when_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "src").mkdir()
            (repo / "src" / "payment_service.py").write_text("", encoding="utf-8")
            run_script(str(SCAN), str(repo))
            # write_minimal_harness lists auth/billing/... but not payments
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("must mention payments", result.stdout)


if __name__ == "__main__":
    unittest.main()
