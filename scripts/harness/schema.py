"""Schema v2 placeholder fields for repo-facts.json."""

from __future__ import annotations

from typing import Any


def v2_placeholders() -> dict[str, Any]:
    return {
        "total_files": 0,
        "top_level_file_counts": {},
        "ignored_top_dirs": [],
        "submodules": [],
        "truncation_strategy": {},
        "suggested_shards": [],
        "test_files_total": 0,
        "test_files_truncated": False,
        "generated_candidates_total": 0,
        "generated_candidates_truncated": False,
        "risk_candidates_total": 0,
        "risk_candidates_truncated": False,
        "important_flow_candidates_total": 0,
        "important_flow_candidates_truncated": False,
        "docs_total": 0,
        "docs_truncated": False,
        "ci_configs_total": 0,
        "ci_configs_truncated": False,
        "makefile_targets_total": 0,
        "makefile_targets_truncated": False,
        "doc_hints_total": 0,
        "doc_hints_truncated": False,
        "ecosystem_hypotheses": [],
        "command_provenance_index": [],
        "ci_commands": [],
        "dockerfile_directives": [],
        "tool_configs": {},
        "env_keys": [],
        "precommit_hooks_detail": [],
        "codeowners": [],
        "makefile_phony_targets": [],
        "python_scripts": {},
        "cargo_workspace_members": [],
        "cargo_binaries": [],
        "go_work_modules": [],
        "justfile_recipes": [],
        "taskfile_tasks": [],
        "docker_services": [],
        "workspace_packages": [],
        "parse_errors": [],
        "content_read_truncated": [],
    }
