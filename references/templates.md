# Harness Templates

Use these templates when creating a harness. Replace placeholders from `.agent/repo-facts.json` (field guide: `references/repo-facts.md`). If the fact is absent after deep scanning, write `Not configured` or `Needs human confirmation` instead of noisy TODOs. If `truncated` is true, note that lists come from a sample.

## AGENTS.md

````md
# Agent Instructions

## Read First
- docs/project-map.md
- docs/testing.md
- docs/dangerous-areas.md
- docs/debugging.md

## Default Workflow
1. Understand the task.
2. Check current workspace state.
3. Search for relevant files before editing.
4. Make the smallest safe change.
5. Add or update tests when behavior changes.
6. Run ./scripts/check.sh.
7. Report changed files, validation results, and remaining risks.

## Do Not
- Edit generated files directly.
- Modify secrets or local environment files.
- Change auth, billing, permissions, migrations, infra, or public APIs without calling out the risk.
- Hide failing or skipped checks.

## Large or High-Risk Changes
Use docs/agent-plan-template.md before editing. Stop after the plan for high-risk areas and ask for human review.
````

## docs/project-map.md

````md
# Project Map

## Snapshot
- Generated from: .agent/repo-facts.json
- Last updated: TODO: date

## Main Directories
List detected top-level directories and observed purpose from scan/docs.

## Detected Project Files
List package manifests, build files, framework files, environment files, and entry docs.

## Important Flows
List flows from `important_flow_candidates`, README/architecture docs, and module AGENTS.md files. Use `Needs human confirmation` only when candidates conflict.

## Generated Files
List confirmed build outputs and generated candidates. Use `Needs human confirmation` for ambiguous code-generation templates or script output artifacts.

## Ownership / Risk
- Owners: list `codeowners` entries. If none, write `Needs human confirmation`.
- High risk: auth, permissions, billing, migrations, infra, secrets, public APIs, generated clients
- Medium risk: shared libraries, background jobs, API handlers
- Low risk: docs, isolated tests, UI copy
````

## docs/testing.md

````md
# Testing

## Verified Commands
List only commands found in repo scripts or successfully run.

## Candidate Commands
List commands detected but not verified, with their source: `package_commands`, `makefile_targets`, `justfile_recipes`, `taskfile_tasks`, `python_scripts`, `ci_commands` (file and line). If none, write `None detected`.

## Test Locations
List detected test directories and patterns. If none, write `Not configured: no dedicated test files detected`.

## Standard Check
Run:

```sh
./scripts/check.sh
```

## Notes
Do not claim checks passed unless they were run in this workspace.
````

## docs/dangerous-areas.md

````md
# Dangerous Areas

## High-Risk Areas
List every reason in `risk_candidates` with its paths (auth, permissions, billing, payments, migrations, deployment, infra, Kubernetes/Helm, IAM/RBAC, PII, secrets, generated files, public API), plus `generated_candidates`. List `env_keys` by name only and point to `security_md` when present.

## Rules
- Do not edit generated files directly.
- Do not change auth, billing, permissions, migrations, infra, secrets, or public APIs without explicit risk notes and focused verification.
- Do not drop or rename persisted data without a compatibility plan.
- Do not change release or deployment scripts casually.

## Mechanical Checks To Add
List checks that would reduce review risk. Use `Recommended:` prefix, not TODO, unless the user asked to implement them now.
````

## docs/debugging.md

````md
# Debugging

## Start Here
- Check docs/testing.md for verified commands.
- Check logs and dev commands documented in this file.

## Local Logs
Document log locations from repo facts (`docker_services`, `dockerfile_directives`, docs). If this is frontend-only or no logs exist, write `Not configured`.

## Common Failures
Document only known failures from repo docs, commands, hooks, or reproduced errors.

## Useful Commands
List verified debug commands. Put unverified commands under a separate candidate section.
````

## docs/agent-plan-template.md

````md
# Agent Plan

## Goal
TODO

## Files Likely Involved
TODO

## Risks
Auth? Billing? Permissions? Migrations? Infra? Public API? Generated files?

## Plan
1. TODO

## Validation
- Unit tests: TODO
- Integration tests: TODO
- Manual checks: TODO
- Commands to run: TODO

## Rollback
TODO
````

## scripts/check.sh

````sh
#!/usr/bin/env sh
set -eu

echo "Harness check"

# Keep only the blocks whose wrapper script exists in this repo. Delete a block
# whose script is absent so validation does not flag a missing reference.

if [ -x ./scripts/format.sh ]; then
  ./scripts/format.sh
else
  echo "TODO: no verified format command configured"
fi

if [ -x ./scripts/lint.sh ]; then
  ./scripts/lint.sh
else
  echo "TODO: no verified lint command configured"
fi

if [ -x ./scripts/typecheck.sh ]; then
  ./scripts/typecheck.sh
else
  echo "TODO: no verified typecheck command configured"
fi

if [ -x ./scripts/test.sh ]; then
  ./scripts/test.sh
else
  echo "TODO: no verified test command configured"
fi

if [ -x ./scripts/build.sh ]; then
  ./scripts/build.sh
else
  echo "TODO: no verified build command configured"
fi
````
