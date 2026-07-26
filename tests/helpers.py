"""Shared test utilities for harness script tests."""

from __future__ import annotations

import subprocess
import sys
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
