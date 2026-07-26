"""Conservative repository fact detectors."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .rules import (
    CI_CONFIG_DIRS,
    CI_CONFIG_NAMES,
    CONFIG_NAMES,
    DOC_NAMES,
    GENERATED_HINTS,
    IMPORTANT_FLOW_HINTS,
    MANIFEST_ECOSYSTEM,
    MANIFEST_NAMES,
    RISK_KEYWORDS,
    SCRIPT_DIRS,
    SKIP_DIRS,
    TEST_EXACT_FILENAMES,
    TEST_HINTS,
)
from .walker import rel

def detect_manifests(files: list[Path], root: Path) -> list[str]:
    return [rel(path, root) for path in files if path.name in MANIFEST_NAMES]


def detect_ecosystem_hypotheses(manifests: list[str]) -> list[dict[str, Any]]:
    by_eco: dict[str, list[str]] = {}
    for m in manifests:
        eco = MANIFEST_ECOSYSTEM.get(Path(m).name)
        if eco:
            by_eco.setdefault(eco, []).append(Path(m).name)
    return [
        {"ecosystem": eco, "hint": f"{eco} ecosystem detected", "evidence": sorted(names)}
        for eco, names in sorted(by_eco.items())
    ]


def detect_tests(files: list[Path], root: Path) -> list[str]:
    hits: list[str] = []
    for path in files:
        parts = [part.lower() for part in path.relative_to(root).parts]
        name = path.name.lower()
        if (
            any(part in TEST_HINTS for part in parts)
            or any(hint in name for hint in (".test.", ".spec.", "_test."))
            or name in TEST_EXACT_FILENAMES
        ):
            hits.append(rel(path, root))
    return hits[:200]


def detect_generated(files: list[Path], root: Path) -> list[str]:
    hits: list[str] = []
    for path in files:
        relative = rel(path, root).lower()
        if any(hint in relative for hint in GENERATED_HINTS):
            hits.append(rel(path, root))
    return hits[:200]


def detect_risks(files: list[Path], root: Path) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    risks: list[dict[str, str]] = []
    for path in files:
        relative = rel(path, root)
        lowered = relative.lower()
        for keyword, reason in RISK_KEYWORDS.items():
            if keyword in lowered:
                key = (relative, reason)
                if key not in seen:
                    risks.append({"path": relative, "reason": reason})
                    seen.add(key)
                break
    return risks[:200]


def detect_existing_scripts(root: Path) -> list[str]:
    results: list[str] = []
    for dir_name in SCRIPT_DIRS:
        script_dir = root / dir_name
        if not script_dir.is_dir():
            continue
        for current, dirs, names in os.walk(script_dir):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            current_path = Path(current)
            for name in sorted(names):
                results.append((current_path / name).relative_to(root).as_posix())
    return results


def detect_ci_configs(files: list[Path], root: Path) -> list[str]:
    hits: list[str] = []
    for path in files:
        relative = rel(path, root)
        parts = path.relative_to(root).parts
        if path.name in CI_CONFIG_NAMES:
            hits.append(relative)
        elif parts and parts[0] in CI_CONFIG_DIRS:
            hits.append(relative)
    return hits[:100]


def detect_precommit_hooks(root: Path) -> list[str]:
    hooks: list[str] = []
    candidates = [
        root / ".pre-commit-config.yaml",
        root / ".pre-commit-hooks.yaml",
    ]
    for path in candidates:
        if path.exists():
            hooks.append(path.relative_to(root).as_posix())
    husky_dir = root / ".husky"
    if husky_dir.is_dir():
        for child in sorted(husky_dir.iterdir(), key=lambda p: p.name):
            if child.is_file():
                hooks.append(child.relative_to(root).as_posix())
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            if "lint-staged" in data or (isinstance(data.get("scripts"), dict) and "prepare" in data["scripts"]):
                hooks.append("package.json#lint-staged/prepare (candidate)")
        except (json.JSONDecodeError, OSError):
            pass
    return hooks


def extract_makefile_targets(root: Path) -> list[str]:
    makefile = root / "Makefile"
    if not makefile.exists():
        return []
    try:
        lines = makefile.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    targets: list[str] = []
    pattern = re.compile(r"^([a-zA-Z][a-zA-Z0-9_\-]*):")
    for line in lines:
        match = pattern.match(line)
        if match:
            targets.append(match.group(1))
    return targets[:50]


def detect_package_scripts(root: Path) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for package_json in root.rglob("package.json"):
        if any(part in SKIP_DIRS for part in package_json.relative_to(root).parts):
            continue
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        scripts = data.get("scripts")
        if isinstance(scripts, dict):
            results[rel(package_json, root)] = sorted(str(name) for name in scripts.keys())
    return results


def detect_configs(files: list[Path], root: Path) -> list[str]:
    return [rel(path, root) for path in files if path.name in CONFIG_NAMES or path.name.startswith(".env")]


def detect_docs(files: list[Path], root: Path) -> list[str]:
    docs: list[str] = []
    for path in files:
        relative = rel(path, root)
        if path.name in DOC_NAMES or (relative.startswith("docs/") and path.suffix.lower() == ".md"):
            docs.append(relative)
    return docs[:200]


def detect_important_flows(files: list[Path], root: Path) -> list[dict[str, str]]:
    flows: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in files:
        relative = rel(path, root)
        lowered = relative.lower()
        for hint, purpose in sorted(IMPORTANT_FLOW_HINTS.items(), key=lambda item: len(item[0]), reverse=True):
            if hint.lower() in lowered and relative not in seen:
                flows.append({"path": relative, "purpose": purpose})
                seen.add(relative)
                break
    return flows[:200]


def detect_script_commands(root: Path) -> dict[str, str]:
    package_json = root / "package.json"
    if not package_json.exists():
        return {}
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(name): str(command) for name, command in sorted(scripts.items())}


def detect_missing_capabilities(root: Path, package_commands: dict[str, str], test_files: list[str]) -> list[str]:
    missing: list[str] = []
    has_package_json = (root / "package.json").exists()
    # Only judge package.json lint capability for JS/TS repos; otherwise this is a
    # misleading fact for Python/Go/Java/Rust repos that never use package.json.
    if has_package_json and not any(name in package_commands for name in ("lint", "lint:fix", "eslint")):
        missing.append("No package.json lint script detected.")
    if not any(name in package_commands for name in ("test", "test:unit", "test:e2e")) and not test_files:
        missing.append("No dedicated test runner or test files detected.")
    lint_sh = any((root / d / "lint.sh").exists() for d in SCRIPT_DIRS)
    if not lint_sh:
        missing.append("No lint.sh wrapper detected in scripts/, bin/, tools/, hack/, or ci/.")
    test_sh = any((root / d / "test.sh").exists() for d in SCRIPT_DIRS)
    if not test_sh:
        missing.append("No test.sh wrapper detected in scripts/, bin/, tools/, hack/, or ci/.")
    typecheck_sh = any((root / d / "typecheck.sh").exists() for d in SCRIPT_DIRS)
    if not typecheck_sh:
        missing.append("No typecheck.sh wrapper detected in scripts/, bin/, tools/, hack/, or ci/.")
    return missing


def extract_doc_hints(root: Path, doc_paths: list[str], max_docs: int = 8) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    patterns = re.compile(
        r"(pnpm|npm|yarn|bun|pytest|vitest|jest|playwright|type-check|build|dev|test|lint|generated|swagger|auth|permission|workflow)",
        re.IGNORECASE,
    )
    for relative in doc_paths[:max_docs]:
        path = root / relative
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        matches = []
        for number, line in enumerate(lines, start=1):
            if patterns.search(line):
                matches.append({"line": number, "text": line.strip()[:240]})
            if len(matches) >= 20:
                break
        if matches:
            hints.append({"path": relative, "matches": matches})
    return hints
