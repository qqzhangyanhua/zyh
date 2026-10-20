"""Harness documentation validator."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .rules import (
    REQUIRED_AGENTS_REFERENCES,
    REQUIRED_FILES,
    RISK_MENTION_RULES,
    RUNTIME_GUESS_PATTERNS,
    UNVERIFIED_COMMANDS,
)

UNSUPPORTED_SCHEMA_KEY = "_unsupported_schema"
SCHEMA_V1_ERROR = (
    "repo-facts.json is schema v1 and no longer supported. "
    "Re-run: python3 scripts/scan_repo.py <repo-root>"
)


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
    schema_version = data.get("schema_version", 1)
    if not isinstance(schema_version, int) or schema_version < 2:
        fail(errors, SCHEMA_V1_ERROR)
        return {UNSUPPORTED_SCHEMA_KEY: True}
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
    # Only require labels whose risk reasons were actually detected in this repo.
    risk_reasons = " ".join(
        item.get("reason", "") for item in facts.get("risk_candidates", [])
    ).lower()
    for label, reason_markers, doc_words in RISK_MENTION_RULES:
        if not any(marker in risk_reasons for marker in reason_markers):
            continue
        if not any(re.search(rf"\b{re.escape(word)}", text) for word in doc_words):
            fail(errors, f"docs/dangerous-areas.md must mention {label} (detected in repo)")


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
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for command in UNVERIFIED_COMMANDS:
        # Whole-word match so "detox" or "scripts/pytest.sh" are not mistaken for tox/pytest.
        if re.search(rf"(?<![\w./-]){re.escape(command)}(?![\w-])", code):
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
            fail(errors, f"{path.relative_to(root)} uses 'Unknown'; write 'Not configured' or 'Needs human confirmation' instead")
