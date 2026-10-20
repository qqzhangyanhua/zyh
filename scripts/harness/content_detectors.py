"""Content-layer detectors: CI commands, Dockerfile directives, tool configs,
.env example keys, pre-commit hook ids, CODEOWNERS, SECURITY.md summary.

All reads share a single ContentBudget so one oversized repo can't blow up
scan time or memory; files skipped once the budget is exhausted are recorded
in `content_read_truncated` instead of silently dropped.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from .walker import rel

_RUN_RE = re.compile(r"^(\s*)(?:-\s*)?run:\s*(.*)$")
_BLOCK_SCALARS = {"|", "|-", "|+", ">", ">-", ">+"}
_DOCKERFILE_DIRECTIVE_RE = re.compile(r"^\s*(RUN|CMD|ENTRYPOINT|WORKDIR|USER|EXPOSE)\s+(.+)$")
_ENV_KEY_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)=")
_PRECOMMIT_REPO_RE = re.compile(r"^\s*-\s*repo:\s*(.+?)\s*$")
_PRECOMMIT_HOOK_ID_RE = re.compile(r"^\s*-\s*id:\s*(.+?)\s*$")

_ENV_SUFFIXES = (".example", ".sample", ".template")
_CODEOWNERS_LOCATIONS = ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")
_SECURITY_LOCATIONS = ("SECURITY.md", ".github/SECURITY.md")
_GENERIC_TOOL_NAMES = ("ruff", "mypy", "black")

_CI_COMMAND_LIMIT = 500
_DOCKERFILE_DIRECTIVE_LIMIT = 500
_ENV_KEY_LIMIT = 200
_CODEOWNERS_LIMIT = 200


class ContentBudget:
    def __init__(self, max_bytes: int) -> None:
        self.remaining = max_bytes

    def try_consume(self, size: int) -> bool:
        if size > self.remaining:
            return False
        self.remaining -= size
        return True


def _read_within_budget(
    path: Path,
    budget: ContentBudget,
    content_read_truncated: list[dict[str, str]],
    rel_path: str,
    kind: str,
) -> str | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if not budget.try_consume(size):
        content_read_truncated.append({"file": rel_path, "kind": kind, "reason": "budget_exceeded"})
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def extract_ci_commands(
    ci_files: list[str], root: Path, budget: ContentBudget, content_read_truncated: list[dict[str, str]]
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for rel_path in ci_files:
        text = _read_within_budget(root / rel_path, budget, content_read_truncated, rel_path, "ci_workflow")
        if text is None:
            continue
        lines = text.splitlines()
        workflow = Path(rel_path).stem
        for i, line in enumerate(lines):
            m = _RUN_RE.match(line)
            if not m:
                continue
            value = m.group(2).strip()
            if value in _BLOCK_SCALARS:
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    commands.append(
                        {
                            "file": rel_path,
                            "line": j + 1,
                            "command": lines[j].strip(),
                            "workflow": workflow,
                            "source": "ci_workflow",
                            "multiline": True,
                        }
                    )
            elif value:
                commands.append(
                    {
                        "file": rel_path,
                        "line": i + 1,
                        "command": value,
                        "workflow": workflow,
                        "source": "ci_workflow",
                        "multiline": False,
                    }
                )
    return commands[:_CI_COMMAND_LIMIT]


def extract_dockerfile_directives(
    files: list[Path], root: Path, budget: ContentBudget, content_read_truncated: list[dict[str, str]]
) -> list[dict[str, Any]]:
    directives: list[dict[str, Any]] = []
    for path in files:
        if "dockerfile" not in path.name.lower():
            continue
        rel_path = rel(path, root)
        text = _read_within_budget(path, budget, content_read_truncated, rel_path, "dockerfile")
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            m = _DOCKERFILE_DIRECTIVE_RE.match(line)
            if m:
                directives.append(
                    {"file": rel_path, "line": line_no, "directive": m.group(1), "value": m.group(2).strip()}
                )
    return directives[:_DOCKERFILE_DIRECTIVE_LIMIT]


def extract_tool_configs(
    root: Path,
    budget: ContentBudget,
    content_read_truncated: list[dict[str, str]],
    errors: list[dict[str, str]],
) -> dict[str, list[str]]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    text = _read_within_budget(pyproject, budget, content_read_truncated, "pyproject.toml", "tool_configs")
    if text is None:
        return {}
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        errors.append({"file": "pyproject.toml", "kind": "toml_parse", "message": str(exc)})
        return {}
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return {}
    configs: dict[str, list[str]] = {}
    pytest_section = tool.get("pytest")
    if isinstance(pytest_section, dict) and isinstance(pytest_section.get("ini_options"), dict):
        configs["pytest.ini_options"] = sorted(pytest_section["ini_options"])
    for name in _GENERIC_TOOL_NAMES:
        section = tool.get(name)
        if isinstance(section, dict):
            configs[name] = sorted(section)
    coverage = tool.get("coverage")
    if isinstance(coverage, dict):
        configs["coverage"] = sorted(coverage)
        for sub_name, sub in coverage.items():
            if isinstance(sub, dict):
                configs[f"coverage.{sub_name}"] = sorted(sub)
    return configs


def extract_env_keys(
    files: list[Path],
    root: Path,
    budget: ContentBudget,
    content_read_truncated: list[dict[str, str]],
    errors: list[dict[str, str]],
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for path in files:
        lower = path.name.lower()
        if not lower.startswith(".env"):
            continue
        rel_path = rel(path, root)
        if not lower.endswith(_ENV_SUFFIXES):
            errors.append(
                {"file": rel_path, "kind": "skipped_dotenv", "message": "real .env file skipped; values are never read"}
            )
            continue
        text = _read_within_budget(path, budget, content_read_truncated, rel_path, "env_example")
        if text is None:
            continue
        for line in text.splitlines():
            m = _ENV_KEY_RE.match(line.strip())
            if m:
                results.append({"file": rel_path, "key": m.group(1)})
    return results[:_ENV_KEY_LIMIT]


def extract_precommit_hooks_detail(
    root: Path,
    budget: ContentBudget,
    content_read_truncated: list[dict[str, str]],
) -> list[dict[str, str | None]]:
    for name in (".pre-commit-config.yaml", ".pre-commit-hooks.yaml"):
        path = root / name
        if not path.exists():
            continue
        text = _read_within_budget(path, budget, content_read_truncated, name, "precommit")
        if text is None:
            return []
        hooks: list[dict[str, str | None]] = []
        current_repo: str | None = None
        for line in text.splitlines():
            repo_m = _PRECOMMIT_REPO_RE.match(line)
            if repo_m:
                current_repo = _strip_quotes(repo_m.group(1))
                continue
            hook_m = _PRECOMMIT_HOOK_ID_RE.match(line)
            if hook_m:
                hooks.append({"repo": current_repo, "hook_id": _strip_quotes(hook_m.group(1))})
        if hooks:
            return hooks
    return []


def extract_codeowners(
    root: Path, budget: ContentBudget, content_read_truncated: list[dict[str, str]]
) -> list[dict[str, Any]]:
    for rel_path in _CODEOWNERS_LOCATIONS:
        path = root / rel_path
        if not path.exists():
            continue
        text = _read_within_budget(path, budget, content_read_truncated, rel_path, "codeowners")
        if text is None:
            return []
        entries: list[dict[str, Any]] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            entries.append({"pattern": parts[0], "owners": parts[1:], "source_line": line_no})
        return entries[:_CODEOWNERS_LIMIT]
    return []


def extract_security_md(
    root: Path, budget: ContentBudget, content_read_truncated: list[dict[str, str]]
) -> dict[str, str] | None:
    for rel_path in _SECURITY_LOCATIONS:
        path = root / rel_path
        if not path.exists():
            continue
        text = _read_within_budget(path, budget, content_read_truncated, rel_path, "security_md")
        if text is None:
            return None
        summary = " ".join(text.split())[:200]
        return {"path": rel_path, "summary": summary}
    return None
