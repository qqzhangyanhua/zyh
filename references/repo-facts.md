# repo-facts.json (schema v2)

`scripts/scan_repo.py` writes `.agent/repo-facts.json`. Every entry is a candidate fact, not a verified claim. Use this page to map fields into harness docs.

## Coverage

| Field | Meaning |
| --- | --- |
| `total_files`, `top_level_file_counts` | Files in scope (git: tracked + untracked, not ignored). Root-level files are counted under `.` |
| `scanned_file_count`, `scan_limit` | Files actually read by detectors and the requested `--limit` (capped at 50000) |
| `truncated` | `true` when fewer files were scanned than exist |
| `truncation_strategy`, `suggested_shards` | Set when sampling happened: files are sampled per top-level directory in proportion to its size. Scan a shard directly when it matters |
| `<field>_total`, `<field>_truncated` | True count and whether the list was capped at 500 (`--full` writes uncapped lists to `repo-facts.full.json`) |
| `ignored_top_dirs`, `submodules` | Gitignored top-level directories and submodules; submodule contents are not scanned |

## Commands (candidates only, never verified by the scan)

| Field | Source |
| --- | --- |
| `package_commands`, `package_scripts`, `workspace_packages` | `package.json` scripts and workspaces |
| `makefile_targets`, `makefile_phony_targets` | Makefile and its includes |
| `python_scripts` | `pyproject.toml` script tables, uv workspace members, poetry groups |
| `justfile_recipes`, `taskfile_tasks`, `docker_services` | Justfile, Taskfile, docker-compose |
| `cargo_workspace_members`, `cargo_binaries`, `go_work_modules` | Cargo.toml, go.work |
| `ci_commands` | `run:` (GitHub Actions, CircleCI `command:`) and `script:` lists (GitLab, Bitbucket, Travis). Multi-line blocks report only the first line with `multiline: true` |
| `existing_scripts` | Files under `scripts/`, `bin/`, `tools/`, `hack/`, `ci/` |

## Risk and ownership

| Field | Meaning |
| --- | --- |
| `risk_candidates` | `{path, reason}`; one path can appear once per reason. Matched on path tokens, so names like `author.md` are not flagged |
| `generated_candidates` | Paths that look generated |
| `codeowners` | CODEOWNERS entries; use for ownership instead of guessing |
| `env_keys` | Key names from `.env.example` / `.sample` / `.template`; real `.env` files are never read |
| `security_md` | Path and first 200 characters of SECURITY.md |

## Other

`manifests`, `ecosystem_hypotheses`, `configs`, `docs`, `doc_hints` (deep mode), `ci_configs`, `precommit_hooks`, `precommit_hooks_detail`, `tool_configs`, `dockerfile_directives`, `test_files`, `important_flow_candidates`, `missing_capabilities`, `parse_errors`, `content_read_truncated`.
