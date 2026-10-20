"""Tests for validate_harness_docs.py CLI behaviour."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_tests_dir = str(Path(__file__).resolve().parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)
from helpers import SCAN, VALIDATE, run_script, write_minimal_harness


class HarnessValidateTests(unittest.TestCase):
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
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")
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

    def test_validate_requires_payments_when_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "src").mkdir()
            (repo / "src" / "payment_service.py").write_text("", encoding="utf-8")
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("must mention payments", result.stdout)

    def _write_dangerous_doc(self, repo: Path, body: str) -> None:
        (repo / "docs/dangerous-areas.md").write_text(f"# Dangerous Areas\n\n{body}\n", encoding="utf-8")

    def test_validate_requires_kubernetes_when_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            (repo / "k8s").mkdir(parents=True)
            (repo / "k8s" / "app.yaml").write_text("", encoding="utf-8")
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")

            rejected = run_script(str(VALIDATE), str(repo))
            self.assertEqual(rejected.returncode, 1)
            self.assertIn("must mention kubernetes", rejected.stdout)

            self._write_dangerous_doc(repo, "- K8s manifests under k8s/")
            accepted = run_script(str(VALIDATE), str(repo))
            self.assertEqual(accepted.returncode, 0, accepted.stdout)

    def test_validate_requires_access_control_for_iam_and_rbac(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            (repo / "iam").mkdir(parents=True)
            (repo / "iam" / "policy.py").write_text("", encoding="utf-8")
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")
            self._write_dangerous_doc(repo, "- william wrote this")

            rejected = run_script(str(VALIDATE), str(repo))
            self.assertEqual(rejected.returncode, 1)
            self.assertIn("must mention access control", rejected.stdout)

            self._write_dangerous_doc(repo, "- IAM policies under iam/")
            accepted = run_script(str(VALIDATE), str(repo))
            self.assertEqual(accepted.returncode, 0, accepted.stdout)

    def test_validate_requires_pii_and_stripe_payments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            (repo / "src").mkdir(parents=True)
            (repo / "src" / "pii_handler.py").write_text("", encoding="utf-8")
            (repo / "src" / "stripe_webhook.py").write_text("", encoding="utf-8")
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")
            self._write_dangerous_doc(repo, "- nothing here")

            rejected = run_script(str(VALIDATE), str(repo))
            self.assertEqual(rejected.returncode, 1)
            self.assertIn("must mention personally identifiable information", rejected.stdout)
            self.assertIn("must mention payments", rejected.stdout)

            self._write_dangerous_doc(repo, "- PII handling in src/pii_handler.py\n- Stripe payment webhook")
            accepted = run_script(str(VALIDATE), str(repo))
            self.assertEqual(accepted.returncode, 0, accepted.stdout)

    def test_validate_ignores_unverified_commands_in_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(
                repo, "#!/usr/bin/env sh\nset -eu\n# pytest is a candidate; see docs/testing.md\necho detox\n"
            )

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 0, result.stdout)

    def test_validate_rejects_extended_unverified_commands(self) -> None:
        for command, label in (
            ("npx jest", "jest"),
            ("./gradlew test", "./gradlew test"),
            ("pnpm run test", "pnpm run test"),
            ("bundle exec rspec", "rspec"),
        ):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as temp_dir:
                repo = Path(temp_dir) / "repo"
                repo.mkdir()
                run_script(str(SCAN), str(repo))
                write_minimal_harness(repo, f"#!/usr/bin/env sh\nset -eu\n{command}\n")

                result = run_script(str(VALIDATE), str(repo))

                self.assertEqual(result.returncode, 1)
                self.assertIn(f"unverified command: {label}", result.stdout)

    def test_validate_unknown_message_points_to_explicit_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            run_script(str(SCAN), str(repo))
            write_minimal_harness(repo, "#!/usr/bin/env sh\nset -eu\n")
            (repo / "docs/debugging.md").write_text("# Debugging\n\nUnknown logs.\n", encoding="utf-8")

            result = run_script(str(VALIDATE), str(repo))

            self.assertEqual(result.returncode, 1)
            self.assertIn("Not configured", result.stdout)
            self.assertIn("Needs human confirmation", result.stdout)


if __name__ == "__main__":
    unittest.main()
