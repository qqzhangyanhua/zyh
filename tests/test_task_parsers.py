"""Tests for Issue #6: task system parsers (Makefile, pyproject, Cargo, go.work, Justfile, YAML)."""

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

from harness.task_parsers import (
    _parse_yaml_section_keys,
    extract_cargo_info,
    extract_docker_services,
    extract_go_work_modules,
    extract_justfile_recipes,
    extract_makefile_info,
    extract_pyproject_scripts,
    extract_taskfile_tasks,
    extract_workspace_packages,
)
from helpers import SCAN, run_script


class MakefileParserTests(unittest.TestCase):
    def test_basic_targets_and_phony(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Makefile").write_text(
                ".PHONY: build test clean\n\nbuild:\n\tgo build ./...\n\ntest:\n\tgo test ./...\n\nclean:\n\trm -rf dist\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            info = extract_makefile_info(repo, errors)
            self.assertIn("build", info["targets"])
            self.assertIn("test", info["targets"])
            self.assertIn("clean", info["targets"])
            self.assertIn("build", info["phony"])
            self.assertIn("test", info["phony"])
            self.assertIn("clean", info["phony"])
            self.assertEqual(errors, [])

    def test_target_limit_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            lines = [f"target{i}:\n\techo {i}" for i in range(250)]
            (repo / "Makefile").write_text("\n".join(lines), encoding="utf-8")
            errors: list[dict] = []
            info = extract_makefile_info(repo, errors)
            self.assertEqual(len(info["targets"]), 200)
            self.assertTrue(info["targets_truncated"])
            self.assertEqual(info["targets_total"], 250)

    def test_include_directive_depth_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "common.mk").write_text("shared:\n\techo shared\n", encoding="utf-8")
            (repo / "Makefile").write_text("include common.mk\n\nbuild:\n\tgo build\n", encoding="utf-8")
            errors: list[dict] = []
            info = extract_makefile_info(repo, errors)
            self.assertIn("shared", info["targets"])
            self.assertIn("build", info["targets"])

    def test_include_directive_depth_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "deep.mk").write_text("deep-target:\n\techo deep\n", encoding="utf-8")
            (repo / "mid.mk").write_text("include deep.mk\nmid-target:\n\techo mid\n", encoding="utf-8")
            (repo / "Makefile").write_text("include mid.mk\ntop:\n\techo top\n", encoding="utf-8")
            errors: list[dict] = []
            info = extract_makefile_info(repo, errors)
            self.assertIn("top", info["targets"])
            self.assertIn("mid-target", info["targets"])
            self.assertIn("deep-target", info["targets"])

    def test_include_depth_3_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "too-deep.mk").write_text("never-seen:\n\techo never\n", encoding="utf-8")
            (repo / "deep.mk").write_text("include too-deep.mk\ndeep:\n\techo deep\n", encoding="utf-8")
            (repo / "mid.mk").write_text("include deep.mk\nmid:\n\techo mid\n", encoding="utf-8")
            (repo / "Makefile").write_text("include mid.mk\ntop:\n\techo top\n", encoding="utf-8")
            errors: list[dict] = []
            info = extract_makefile_info(repo, errors)
            self.assertIn("top", info["targets"])
            self.assertIn("mid", info["targets"])
            self.assertIn("deep", info["targets"])
            self.assertNotIn("never-seen", info["targets"])

    def test_cycle_prevention(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "a.mk").write_text("include b.mk\na-target:\n\techo a\n", encoding="utf-8")
            (repo / "b.mk").write_text("include a.mk\nb-target:\n\techo b\n", encoding="utf-8")
            (repo / "Makefile").write_text("include a.mk\ntop:\n\techo top\n", encoding="utf-8")
            errors: list[dict] = []
            info = extract_makefile_info(repo, errors)
            self.assertIn("top", info["targets"])
            self.assertIn("a-target", info["targets"])
            self.assertIn("b-target", info["targets"])

    def test_no_makefile_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors: list[dict] = []
            info = extract_makefile_info(Path(tmp), errors)
            self.assertEqual(info["targets"], [])
            self.assertEqual(info["phony"], [])
            self.assertEqual(errors, [])


class PyprojectScriptsTests(unittest.TestCase):
    def test_project_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text(
                '[project]\nname = "app"\n[project.scripts]\nmycli = "app:main"\nother = "app:cli"\n',
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_pyproject_scripts(repo, errors)
            self.assertIn("[project.scripts]", result)
            self.assertIn("mycli", result["[project.scripts]"])
            self.assertIn("other", result["[project.scripts]"])
            self.assertEqual(errors, [])

    def test_poetry_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text(
                '[tool.poetry]\nname = "app"\n[tool.poetry.scripts]\nstart = "app:main"\n',
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_pyproject_scripts(repo, errors)
            self.assertIn("[tool.poetry.scripts]", result)
            self.assertIn("start", result["[tool.poetry.scripts]"])

    def test_hatch_env_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text(
                "[tool.hatch.envs.default.scripts]\ntest = 'pytest'\nlint = 'ruff check .'\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_pyproject_scripts(repo, errors)
            key = "[tool.hatch.envs.default.scripts]"
            self.assertIn(key, result)
            self.assertIn("test", result[key])

    def test_uv_workspace_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text(
                "[tool.uv.workspace]\nmembers = [\"packages/a\", \"packages/b\"]\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_pyproject_scripts(repo, errors)
            self.assertIn("[tool.uv.workspace.members]", result)
            self.assertIn("packages/a", result["[tool.uv.workspace.members]"])

    def test_poetry_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text(
                "[tool.poetry.group.dev.dependencies]\npytest = \"*\"\n[tool.poetry.group.docs.dependencies]\nsphinx = \"*\"\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_pyproject_scripts(repo, errors)
            self.assertIn("[tool.poetry.groups]", result)
            self.assertIn("dev", result["[tool.poetry.groups]"])
            self.assertIn("docs", result["[tool.poetry.groups]"])

    def test_malformed_toml_populates_parse_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text("[[invalid\nbroken toml content here\n", encoding="utf-8")
            errors: list[dict] = []
            result = extract_pyproject_scripts(repo, errors)
            self.assertEqual(result, {})
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["file"], "pyproject.toml")
            self.assertEqual(errors[0]["kind"], "toml_parse")


class CargoInfoTests(unittest.TestCase):
    def test_workspace_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Cargo.toml").write_text(
                '[workspace]\nmembers = ["crate-a", "crate-b", "libs/core"]\n',
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_cargo_info(repo, errors)
            self.assertIn("crate-a", result["workspace_members"])
            self.assertIn("crate-b", result["workspace_members"])
            self.assertIn("libs/core", result["workspace_members"])
            self.assertEqual(errors, [])

    def test_binaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Cargo.toml").write_text(
                '[package]\nname = "myapp"\n[[bin]]\nname = "server"\npath = "src/bin/server.rs"\n[[bin]]\nname = "cli"\npath = "src/bin/cli.rs"\n',
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_cargo_info(repo, errors)
            self.assertIn("server", result["binaries"])
            self.assertIn("cli", result["binaries"])

    def test_malformed_cargo_toml_populates_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Cargo.toml").write_text("[[broken\nstuff\n", encoding="utf-8")
            errors: list[dict] = []
            result = extract_cargo_info(repo, errors)
            self.assertEqual(result["workspace_members"], [])
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["kind"], "toml_parse")


class GoWorkModulesTests(unittest.TestCase):
    def test_use_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "go.work").write_text(
                "go 1.21\n\nuse (\n    ./service-a\n    ./service-b\n    ./libs/core\n)\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_go_work_modules(repo, errors)
            self.assertIn("./service-a", result)
            self.assertIn("./service-b", result)
            self.assertIn("./libs/core", result)
            self.assertEqual(errors, [])

    def test_single_use_directive(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "go.work").write_text("go 1.21\n\nuse ./standalone\n", encoding="utf-8")
            errors: list[dict] = []
            result = extract_go_work_modules(repo, errors)
            self.assertIn("./standalone", result)


class JustfileRecipesTests(unittest.TestCase):
    def test_basic_recipes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Justfile").write_text(
                "# comment\nbuild:\n    cargo build\n\ntest:\n    cargo test\n\nclean:\n    rm -rf target\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_justfile_recipes(repo, errors)
            self.assertIn("build", result)
            self.assertIn("test", result)
            self.assertIn("clean", result)
            self.assertEqual(errors, [])

    def test_at_prefix_recipes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Justfile").write_text("@silent-recipe:\n    echo quiet\n", encoding="utf-8")
            errors: list[dict] = []
            result = extract_justfile_recipes(repo, errors)
            self.assertIn("silent-recipe", result)

    def test_keywords_not_treated_as_recipes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Justfile").write_text(
                "set shell := ['bash', '-c']\n\nbuild:\n    cargo build\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_justfile_recipes(repo, errors)
            self.assertNotIn("set", result)
            self.assertIn("build", result)


class YamlSectionParserTests(unittest.TestCase):
    def test_taskfile_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Taskfile.yml").write_text(
                "version: '3'\n\ntasks:\n  build:\n    cmds:\n      - go build ./...\n  test:\n    cmds:\n      - go test ./...\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_taskfile_tasks(repo, errors)
            self.assertIn("build", result)
            self.assertIn("test", result)
            self.assertEqual(errors, [])

    def test_docker_compose_services(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "docker-compose.yml").write_text(
                "version: '3.8'\n\nservices:\n  db:\n    image: postgres:15\n  app:\n    build: .\n    ports:\n      - '8080:8080'\n",
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_docker_services(repo, errors)
            self.assertIn("db", result)
            self.assertIn("app", result)
            self.assertEqual(errors, [])

    def test_parse_yaml_section_keys_ignores_nested(self):
        text = "tasks:\n  build:\n    cmds:\n      - echo\n  test:\n    cmds:\n      - pytest\n"
        keys = _parse_yaml_section_keys(text, "tasks")
        self.assertEqual(keys, ["build", "test"])

    def test_no_taskfile_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors: list[dict] = []
            result = extract_taskfile_tasks(Path(tmp), errors)
            self.assertEqual(result, [])
            self.assertEqual(errors, [])


class WorkspacePackagesTests(unittest.TestCase):
    def test_array_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text(
                json.dumps({"name": "root", "workspaces": ["packages/*", "apps/web"]}),
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_workspace_packages(repo, errors)
            self.assertIn("packages/*", result)
            self.assertIn("apps/web", result)
            self.assertEqual(errors, [])

    def test_dict_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text(
                json.dumps({"workspaces": {"packages": ["packages/a", "packages/b"]}}),
                encoding="utf-8",
            )
            errors: list[dict] = []
            result = extract_workspace_packages(repo, errors)
            self.assertIn("packages/a", result)
            self.assertIn("packages/b", result)

    def test_no_workspaces_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text(json.dumps({"name": "simple"}), encoding="utf-8")
            errors: list[dict] = []
            result = extract_workspace_packages(repo, errors)
            self.assertEqual(result, [])


class EndToEndTaskSystemTests(unittest.TestCase):
    def _scan(self, repo: Path, *extra: str) -> dict:
        result = run_script(str(SCAN), *extra, str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        import json as _json
        return _json.loads((repo / ".agent" / "repo-facts.json").read_text(encoding="utf-8"))

    def test_new_fields_present_in_scan_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Makefile").write_text(".PHONY: build\nbuild:\n\tgo build\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("makefile_phony_targets", facts)
            self.assertIn("python_scripts", facts)
            self.assertIn("cargo_workspace_members", facts)
            self.assertIn("cargo_binaries", facts)
            self.assertIn("go_work_modules", facts)
            self.assertIn("justfile_recipes", facts)
            self.assertIn("taskfile_tasks", facts)
            self.assertIn("docker_services", facts)
            self.assertIn("workspace_packages", facts)
            self.assertIn("parse_errors", facts)

    def test_parse_errors_empty_for_clean_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("", encoding="utf-8")
            facts = self._scan(repo)
            self.assertEqual(facts["parse_errors"], [])

    def test_malformed_toml_scan_succeeds_with_parse_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text("[[invalid\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertEqual(len(facts["parse_errors"]), 1)
            self.assertEqual(facts["parse_errors"][0]["file"], "pyproject.toml")

    def test_makefile_phony_in_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Makefile").write_text(
                ".PHONY: build test\nbuild:\n\tgo build\ntest:\n\tgo test ./...\n",
                encoding="utf-8",
            )
            facts = self._scan(repo)
            self.assertIn("build", facts["makefile_phony_targets"])
            self.assertIn("test", facts["makefile_phony_targets"])

    def test_cargo_workspace_in_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Cargo.toml").write_text(
                '[workspace]\nmembers = ["crate-a", "crate-b"]\n',
                encoding="utf-8",
            )
            facts = self._scan(repo)
            self.assertIn("crate-a", facts["cargo_workspace_members"])

    def test_justfile_recipes_in_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Justfile").write_text("build:\n    cargo build\n\ndeploy:\n    ./deploy.sh\n", encoding="utf-8")
            facts = self._scan(repo)
            self.assertIn("build", facts["justfile_recipes"])
            self.assertIn("deploy", facts["justfile_recipes"])


if __name__ == "__main__":
    unittest.main()
