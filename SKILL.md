---
name: harness
description: Use when preparing an unfamiliar legacy or large repository for safe agent work, especially when repo structure, test commands, generated files, or high-risk areas are unclear.
---

# Harness

## Overview

Build an agent harness for legacy repos by turning project facts into small docs and mechanical checks. The core rule: inspect first, fill what can be proven, and never invent architecture or commands.

## When to Use

- User asks for `AGENTS.md`, repo onboarding, Codex harness, agent harness, project map, safe scope, or legacy repo docs.
- The repo is old, large, unfamiliar, multi-module, or has unclear test commands.
- High-risk areas may include auth, permissions, billing, migrations, generated clients, infra, secrets, or public APIs.

Do not use for one-off task docs inside a well-understood small project.

## Required Flow

1. Run `python3 scripts/scan_repo.py <repo>` from this skill directory before writing harness docs.
   - If the user asks to spend more time, reduce TODOs, or finish in one pass, run `python3 scripts/scan_repo.py --deep --limit 20000 <repo>`.
2. Generate or update:
   - `AGENTS.md`
   - `docs/project-map.md`
   - `docs/testing.md`
   - `docs/dangerous-areas.md`
   - `docs/debugging.md`
   - `docs/agent-plan-template.md`
   - `scripts/check.sh`
3. Use `references/templates.md` as the template source.
4. Use facts from `.agent/repo-facts.json`. If a fact is missing, classify it instead of guessing:
   - `Not configured`: the repo scan/docs show the capability is absent.
   - `Needs human confirmation`: the repo has candidates but no source of truth.
   - `TODO`: only for future work the user explicitly wants tracked.
5. Keep `AGENTS.md` as a directory and workflow entry point. Put details in `docs/`.
6. Make `scripts/check.sh` call only existing wrapper scripts or commands explicitly verified during this task. Otherwise it must print TODOs.
7. Run `python3 scripts/validate_harness_docs.py <repo>` from this skill directory before reporting completion.

## Quick Reference

| Need | Use |
| --- | --- |
| Repo facts | `python3 scripts/scan_repo.py /path/to/repo` |
| Deep facts | `python3 scripts/scan_repo.py --deep --limit 20000 /path/to/repo` |
| Templates | `references/templates.md` |
| Validation | `python3 scripts/validate_harness_docs.py /path/to/repo` |
| Missing capability | `Not configured: ...` |
| Ambiguous fact | `Needs human confirmation: ...` |
| High-risk changes | stop after plan and ask for review |

## Rules That Prevent Baseline Failures

- Do not infer package manager, test command, architecture, owners, or generated-file commands.
- Do not put `pnpm test`, `pytest`, `make test`, or similar into `check.sh` just because a manifest exists. Package files create candidate commands, not verified commands.
- Do not make `check.sh` discover tests at runtime with `pnpm run | grep`, `command -v pytest`, or `grep '^test:' Makefile`. Put those candidates in `docs/testing.md` until verified.
- Do not mark high-risk areas as safe because they are common or expected.
- Do not create a huge AGENTS.md. It should point to project docs.
- Do not hide failed or skipped checks. Report them plainly.
- Do not leave TODOs for facts that can be resolved by reading README, architecture docs, package scripts, config files, hooks, or module AGENTS.md files.
- Do not use TODO for intentionally empty state. Write `Not configured` when no test runner, lint script, backend logs, or wrapper script exists.
- Treat `.agent/repo-facts.json` as a regenerable scan artifact. Add `.agent/` to the target repo's `.gitignore` instead of committing it.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Guessing standard monorepo folders | scan top-level paths and write TODO for unclear areas |
| Writing all knowledge into AGENTS.md | keep AGENTS.md short, put details in docs |
| `check.sh` runs unverified commands | call existing scripts only, otherwise print TODO |
| Treating generated files as docs-only advice | add generated paths to dangerous areas and checks |
| Skipping validation because docs are simple | run the validator every time |
| Leaving noisy TODOs after a shallow pass | rerun with `--deep --limit 20000`, read doc hints, and classify unresolved items |
