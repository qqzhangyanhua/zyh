"""CLI entry functions for harness scripts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scanner import scan
from .validator import (
    UNSUPPORTED_SCHEMA_KEY,
    validate_agents,
    validate_check_script,
    validate_dangerous_areas,
    validate_facts,
    validate_required_files,
    validate_todos,
)


def scan_main() -> int:
    parser = argparse.ArgumentParser(description="Scan a repository and write conservative facts for agent harness docs.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository root to scan")
    parser.add_argument("--limit", type=int, default=5000, help="Maximum files to scan")
    parser.add_argument("--deep", action="store_true", help="Collect extra docs, config, flow, and missing-capability facts")
    parser.add_argument("--output", help="Output JSON path; defaults to <repo>/.agent/repo-facts.json")
    args = parser.parse_args()

    root = Path(args.repo)
    if not root.is_dir():
        parser.error(f"repo is not a directory: {root}")

    facts = scan(root, args.limit, args.deep)
    output = Path(args.output) if args.output else root / ".agent" / "repo-facts.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


def validate_main() -> int:
    parser = argparse.ArgumentParser(description="Validate the minimum harness docs for an agent-ready legacy repo.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository root to validate")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []

    facts = validate_facts(root, errors)
    if facts.get(UNSUPPORTED_SCHEMA_KEY):
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    validate_required_files(root, errors)
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
