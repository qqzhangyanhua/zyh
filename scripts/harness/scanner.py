"""Repository scanner orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .detectors import (
    detect_ci_configs,
    detect_configs,
    detect_docs,
    detect_ecosystem_hypotheses,
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
from .sampling import sample_with_buckets
from .schema import v2_placeholders
from .walker import count_files, top_level, walk_repo

_FULL_THRESHOLD = 50_000
_MAX_THRESHOLD = 500_000
_SAMPLE_CAP = 500


class FileLimitError(Exception):
    def __init__(self, total: int, threshold: int) -> None:
        self.total = total
        self.threshold = threshold
        super().__init__(f"repository has {total:,} files (>{threshold:,}); use --force to scan anyway")


def _top_dir(path: str) -> str:
    return path.split("/", 1)[0]


def _top_dir_dict(item: dict) -> str:
    return _top_dir(item.get("path", ""))


def scan(
    root: Path,
    limit: int,
    deep: bool,
    full_output: Path | None = None,
    force: bool = False,
    _full_threshold: int = _FULL_THRESHOLD,
    _max_threshold: int = _MAX_THRESHOLD,
) -> dict[str, Any]:
    root = root.resolve()

    counts = count_files(root)
    total: int = counts["total"]
    by_top: dict[str, int] = counts["by_top_dir"]

    if total > _max_threshold and not force:
        raise FileLimitError(total, _max_threshold)

    if total > _full_threshold and not force:
        walk_limit = _full_threshold
        quota: dict[str, int] | None = {
            top: max(1, round(n / total * _full_threshold)) for top, n in by_top.items()
        }
        truncation_strategy: dict[str, Any] = {
            "mode": "proportional",
            "total_files": total,
            "sample_limit": _full_threshold,
        }
        suggested_shards = sorted(by_top)
    else:
        walk_limit = limit
        quota = None
        truncation_strategy = {}
        suggested_shards: list[str] = []

    walk_result = walk_repo(root, walk_limit, quota)
    files = walk_result.files

    manifests = detect_manifests(files, root)
    test_files_raw = detect_tests(files, root)
    docs_raw = detect_docs(files, root)
    generated_raw = detect_generated(files, root)
    risks_raw = detect_risks(files, root)
    flows_raw = detect_important_flows(files, root)
    ci_configs_raw = detect_ci_configs(files, root)
    makefile_targets_raw = extract_makefile_targets(root)
    package_commands = detect_script_commands(root)

    test_files, tf_total, tf_trunc = sample_with_buckets(test_files_raw, _SAMPLE_CAP, _top_dir)
    docs, docs_total, docs_trunc = sample_with_buckets(docs_raw, _SAMPLE_CAP, _top_dir)
    generated, gen_total, gen_trunc = sample_with_buckets(generated_raw, _SAMPLE_CAP, _top_dir)
    risks, risks_total, risks_trunc = sample_with_buckets(risks_raw, _SAMPLE_CAP, _top_dir_dict)
    flows, flows_total, flows_trunc = sample_with_buckets(flows_raw, _SAMPLE_CAP, _top_dir_dict)
    ci_configs, ci_total, ci_trunc = sample_with_buckets(ci_configs_raw, _SAMPLE_CAP, _top_dir)
    makefile_targets, mk_total, mk_trunc = sample_with_buckets(makefile_targets_raw, _SAMPLE_CAP, lambda x: x)

    facts: dict[str, Any] = {
        **v2_placeholders(),
        "schema_version": 2,
        "scan_mode": "deep" if deep else "standard",
        "scan_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root": root.as_posix(),
        "top_level": top_level(root),
        "total_files": total,
        "top_level_file_counts": by_top,
        "truncation_strategy": truncation_strategy,
        "suggested_shards": suggested_shards,
        "manifests": manifests,
        "ecosystem_hypotheses": detect_ecosystem_hypotheses(manifests),
        "configs": detect_configs(files, root),
        "docs": docs,
        "docs_total": docs_total,
        "docs_truncated": docs_trunc,
        "existing_scripts": detect_existing_scripts(root),
        "ci_configs": ci_configs,
        "ci_configs_total": ci_total,
        "ci_configs_truncated": ci_trunc,
        "precommit_hooks": detect_precommit_hooks(root),
        "makefile_targets": makefile_targets,
        "makefile_targets_total": mk_total,
        "makefile_targets_truncated": mk_trunc,
        "package_scripts": detect_package_scripts(root),
        "package_commands": package_commands,
        "test_files": test_files,
        "test_files_total": tf_total,
        "test_files_truncated": tf_trunc,
        "generated_candidates": generated,
        "generated_candidates_total": gen_total,
        "generated_candidates_truncated": gen_trunc,
        "risk_candidates": risks,
        "risk_candidates_total": risks_total,
        "risk_candidates_truncated": risks_trunc,
        "important_flow_candidates": flows,
        "important_flow_candidates_total": flows_total,
        "important_flow_candidates_truncated": flows_trunc,
        "missing_capabilities": detect_missing_capabilities(root, package_commands, test_files),
        "scanned_file_count": len(files),
        "scan_limit": limit,
        "truncated": len(files) >= walk_limit,
        "doc_hints_total": 0,
        "doc_hints_truncated": False,
        "notes": [
            "Facts are conservative candidates, not architecture claims.",
            "Commands must be verified before docs claim they pass.",
        ],
    }
    facts["ignored_top_dirs"] = walk_result.ignored_top_dirs
    facts["submodules"] = walk_result.submodules

    if deep:
        doc_hints_raw: list[Any] = extract_doc_hints(root, docs_raw)
        doc_hints, dh_total, dh_trunc = sample_with_buckets(
            doc_hints_raw, _SAMPLE_CAP, lambda h: _top_dir(h.get("path", ""))
        )
        facts["doc_hints"] = doc_hints
        facts["doc_hints_total"] = dh_total
        facts["doc_hints_truncated"] = dh_trunc
    else:
        doc_hints_raw = []

    if full_output is not None:
        overrides: dict[str, Any] = {
            "test_files": test_files_raw,
            "test_files_total": len(test_files_raw),
            "test_files_truncated": False,
            "generated_candidates": generated_raw,
            "generated_candidates_total": len(generated_raw),
            "generated_candidates_truncated": False,
            "risk_candidates": risks_raw,
            "risk_candidates_total": len(risks_raw),
            "risk_candidates_truncated": False,
            "important_flow_candidates": flows_raw,
            "important_flow_candidates_total": len(flows_raw),
            "important_flow_candidates_truncated": False,
            "docs": docs_raw,
            "docs_total": len(docs_raw),
            "docs_truncated": False,
            "ci_configs": ci_configs_raw,
            "ci_configs_total": len(ci_configs_raw),
            "ci_configs_truncated": False,
            "makefile_targets": makefile_targets_raw,
            "makefile_targets_total": len(makefile_targets_raw),
            "makefile_targets_truncated": False,
        }
        if deep:
            overrides["doc_hints"] = doc_hints_raw
            overrides["doc_hints_total"] = len(doc_hints_raw)
            overrides["doc_hints_truncated"] = False
        full_output.parent.mkdir(parents=True, exist_ok=True)
        full_output.write_text(
            json.dumps({**facts, **overrides}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    return facts
