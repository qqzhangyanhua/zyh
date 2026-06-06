#!/usr/bin/env python3
"""Validate the minimum harness docs for an agent-ready legacy repo."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


REQUIRED_FILES = [
    "AGENTS.md",
    "docs/project-map.md",
    "docs/testing.md",
    "docs/dangerous-areas.md",
    "docs/debugging.md",
    "docs/agent-plan-template.md",
    "scripts/check.sh",
    ".agent/repo-facts.json",
]

REQUIRED_AGENTS_REFERENCES = [
    "docs/project-map.md",
    "docs/testing.md",
    "docs/dangerous-areas.md",
    "docs/debugging.md",
    "docs/agent-plan-template.md",
]

RISK_TERMS = [
    "auth",
    "permission",
    "billing",
    "payments",
    "migration",
    "deployment",
    "infra",
    "secret",
    "generated",
    "public api",
]

UNVERIFIED_COMMANDS = [
    "pnpm test",
    "npm test",
    "yarn test",
    "bun test",
    "pytest",
    "make test",
    "cargo test",
    "go test",
    "mvn test",
]

RUNTIME_GUESS_PATTERNS = [
    "pnpm run | grep",
    "npm run | grep",
    "yarn run | grep",
    "command -v pytest",
    "command -v pnpm",
    "command -v npm",
    "grep -qE '^test:' Makefile",
    "grep -q '^test:' Makefile",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_required_files(root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (root / relative).exists():
            fail(errors, f"missing required file: {relative}")


def validate_facts(root: Path, errors: list[str]) -> dict:
    path = root / ".agent/repo-facts.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(read(path))
    except json.JSONDecodeError as exc:
        fail(errors, f"invalid JSON in .agent/repo-facts.json: {exc}")
        return {}
    if "root" not in data or "top_level" not in data:
        fail(errors, ".agent/repo-facts.json missing root or top_level")
    return data


def validate_agents(root: Path, errors: list[str]) -> None:
    path = root / "AGENTS.md"
    if not path.exists():
        return
    text = read(path)
    for reference in REQUIRED_AGENTS_REFERENCES:
        if reference not in text:
            fail(errors, f"AGENTS.md must reference {reference}")
    if len(text.splitlines()) > 120:
        fail(errors, "AGENTS.md is too long; keep it as an entry point and move details to docs/")


def validate_dangerous_areas(root: Path, facts: dict, errors: list[str]) -> None:
    path = root / "docs/dangerous-areas.md"
    if not path.exists():
        return
    text = read(path).lower()
    # Only require terms that actually appear as risk candidates in this repo.
    risk_reasons = " ".join(
        item.get("reason", "") for item in facts.get("risk_candidates", [])
    ).lower()
    for term in RISK_TERMS:
        if term not in risk_reasons:
            continue
        if term not in text:
            fail(errors, f"docs/dangerous-areas.md must mention {term} (detected in repo)")


def validate_check_script(root: Path, facts: dict, errors: list[str]) -> None:
    path = root / "scripts/check.sh"
    if not path.exists():
        return
    if not os.access(path, os.X_OK):
        fail(errors, "scripts/check.sh is not executable (run: chmod +x scripts/check.sh)")
    text = read(path)
    if "set -e" not in text:
        fail(errors, "scripts/check.sh must use set -e or set -eu")
    for pattern in RUNTIME_GUESS_PATTERNS:
        if pattern in text:
            fail(errors, f"scripts/check.sh uses runtime command guessing: {pattern}")
    existing_scripts = set(facts.get("existing_scripts", []))
    for command in UNVERIFIED_COMMANDS:
        if command not in text:
            continue
        fail(errors, f"scripts/check.sh includes unverified command: {command}")
    # Match ./scripts/X, scripts/X, ./bin/X, bin/X, and nested paths like
    # scripts/ci/foo.sh — but not inside shebang paths like /usr/bin/env
    for script in re.findall(r"(?<![/\w])\.?/?(?:scripts|bin|tools|hack|ci)/[A-Za-z0-9_./-]+", text):
        normalized = script.lstrip("./")
        if normalized == "scripts/check.sh":
            continue
        if normalized not in existing_scripts:
            fail(errors, f"scripts/check.sh references missing script: {script}")


def validate_todos(root: Path, errors: list[str]) -> None:
    docs = [
        root / "docs/project-map.md",
        root / "docs/testing.md",
        root / "docs/dangerous-areas.md",
        root / "docs/debugging.md",
    ]
    for path in docs:
        if not path.exists():
            continue
        text = read(path)
        if "Unknown" in text:
            fail(errors, f"{path.relative_to(root)} uses 'Unknown'; use explicit TODO markers instead")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=".", help="Repository root to validate")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []

    validate_required_files(root, errors)
    facts = validate_facts(root, errors)
    validate_agents(root, errors)
    validate_dangerous_areas(root, facts, errors)
    validate_check_script(root, facts, errors)
    validate_todos(root, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("harness docs validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
