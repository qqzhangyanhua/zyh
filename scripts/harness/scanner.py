"""Repository scanner orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .detectors import (
    detect_ci_configs,
    detect_configs,
    detect_docs,
    detect_existing_scripts,
    detect_generated,
    detect_important_flows,
    detect_manifests,
    detect_missing_capabilities,
    detect_package_scripts,
    detect_precommit_hooks,
    detect_risks,
    detect_script_commands,
    detect_tests,
    extract_doc_hints,
    extract_makefile_targets,
)
from .schema import v2_placeholders
from .walker import top_level, walk_files

def scan(root: Path, limit: int, deep: bool) -> dict[str, Any]:
    root = root.resolve()
    files = walk_files(root, limit)
    test_files = detect_tests(files, root)
    docs = detect_docs(files, root)
    package_commands = detect_script_commands(root)
    facts: dict[str, Any] = {
        "schema_version": 2,
        "scan_mode": "deep" if deep else "standard",
        "scan_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root": root.as_posix(),
        "top_level": top_level(root),
        "manifests": detect_manifests(files, root),
        "configs": detect_configs(files, root),
        "docs": docs,
        "existing_scripts": detect_existing_scripts(root),
        "ci_configs": detect_ci_configs(files, root),
        "precommit_hooks": detect_precommit_hooks(root),
        "makefile_targets": extract_makefile_targets(root),
        "package_scripts": detect_package_scripts(root),
        "package_commands": package_commands,
        "test_files": test_files,
        "generated_candidates": detect_generated(files, root),
        "risk_candidates": detect_risks(files, root),
        "important_flow_candidates": detect_important_flows(files, root),
        "missing_capabilities": detect_missing_capabilities(root, package_commands, test_files),
        "scanned_file_count": len(files),
        "scan_limit": limit,
        "truncated": len(files) >= limit,
        "notes": [
            "Facts are conservative candidates, not architecture claims.",
            "Commands must be verified before docs claim they pass.",
        ],
        **v2_placeholders(),
    }
    if deep:
        facts["doc_hints"] = extract_doc_hints(root, docs)
    return facts
