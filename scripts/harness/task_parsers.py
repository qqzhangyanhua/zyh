"""Task system parsers: Makefile, pyproject, Cargo, go.work, Justfile, Taskfile, Compose."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

_TARGET_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9_\-]*):(?!=)")
_PHONY_RE = re.compile(r"^\.PHONY\s*:\s*(.*)")
_INCLUDE_RE = re.compile(r"^-?include\s+(\S+)")
_RECIPE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_\-]*)[\s:]")
_YAML_CHILD_RE = re.compile(r"^  ([a-zA-Z_][a-zA-Z0-9_\-]*):")

_JUST_KEYWORDS = frozenset({"if", "else", "for", "while", "set", "export", "import", "alias"})
_TASK_LIMIT = 200


def extract_makefile_info(root: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    targets, phony = _parse_makefile_text(root, "Makefile", set(), 0, errors)
    seen: set[str] = set()
    unique: list[str] = [t for t in targets if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]
    phony_set = {p for p in phony if p in seen}
    return {
        "targets": unique[:_TASK_LIMIT],
        "all_targets": unique,
        "targets_total": len(unique),
        "targets_truncated": len(unique) > _TASK_LIMIT,
        "phony": sorted(phony_set),
    }


def _parse_makefile_text(
    root: Path,
    filename: str,
    visited: set[str],
    depth: int,
    errors: list[dict[str, str]],
) -> tuple[list[str], list[str]]:
    if depth > 2 or filename in visited:
        return [], []
    visited.add(filename)
    filepath = root / filename
    if not filepath.exists():
        return [], []
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        errors.append({"file": filename, "kind": "io", "message": str(exc)})
        return [], []
    targets: list[str] = []
    phony: list[str] = []
    for line in lines:
        inc = _INCLUDE_RE.match(line)
        if inc:
            inc_file = inc.group(1)
            if not inc_file.startswith("/"):
                sub_t, sub_p = _parse_makefile_text(root, inc_file, visited, depth + 1, errors)
                targets.extend(sub_t)
                phony.extend(sub_p)
            continue
        ph = _PHONY_RE.match(line)
        if ph:
            phony.extend(ph.group(1).split())
            continue
        tm = _TARGET_RE.match(line)
        if tm:
            targets.append(tm.group(1))
    return targets, phony


def extract_pyproject_scripts(root: Path, errors: list[dict[str, str]]) -> dict[str, list[str]]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        errors.append({"file": "pyproject.toml", "kind": "toml_parse", "message": str(exc)})
        return {}
    scripts: dict[str, list[str]] = {}
    if isinstance(proj := data.get("project", {}).get("scripts"), dict):
        scripts["[project.scripts]"] = sorted(proj)
    if isinstance(poetry := data.get("tool", {}).get("poetry", {}).get("scripts"), dict):
        scripts["[tool.poetry.scripts]"] = sorted(poetry)
    if isinstance(pdm := data.get("tool", {}).get("pdm", {}).get("scripts"), dict):
        scripts["[tool.pdm.scripts]"] = sorted(pdm)
    hatch_envs = data.get("tool", {}).get("hatch", {}).get("envs", {})
    for env_name, env_data in (hatch_envs.items() if isinstance(hatch_envs, dict) else []):
        if isinstance(env_data, dict) and isinstance(env_data.get("scripts"), dict):
            scripts[f"[tool.hatch.envs.{env_name}.scripts]"] = sorted(env_data["scripts"])
    if isinstance(uv_members := data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members"), list):
        scripts["[tool.uv.workspace.members]"] = [str(m) for m in uv_members]
    poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
    if poetry_groups:
        scripts["[tool.poetry.groups]"] = sorted(poetry_groups)
    return scripts


def extract_cargo_info(root: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    cargo = root / "Cargo.toml"
    if not cargo.exists():
        return {"workspace_members": [], "binaries": []}
    try:
        data = tomllib.loads(cargo.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        errors.append({"file": "Cargo.toml", "kind": "toml_parse", "message": str(exc)})
        return {"workspace_members": [], "binaries": []}
    members = list(data.get("workspace", {}).get("members", []))
    binaries = [b["name"] for b in data.get("bin", []) if isinstance(b, dict) and "name" in b]
    return {"workspace_members": members[:100], "binaries": binaries[:100]}


def extract_go_work_modules(root: Path, errors: list[dict[str, str]]) -> list[str]:
    go_work = root / "go.work"
    if not go_work.exists():
        return []
    try:
        lines = go_work.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        errors.append({"file": "go.work", "kind": "io", "message": str(exc)})
        return []
    modules: list[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if stripped == "use (":
            in_block = True
        elif stripped == ")" and in_block:
            in_block = False
        elif in_block:
            modules.append(stripped)
        elif stripped.startswith("use ") and not stripped.startswith("use ("):
            modules.append(stripped[4:].strip())
    return modules[:100]


def extract_justfile_recipes(root: Path, errors: list[dict[str, str]]) -> list[str]:
    justfile: Path | None = None
    for name in ("Justfile", "justfile", ".justfile"):
        candidate = root / name
        if candidate.exists():
            justfile = candidate
            break
    if justfile is None:
        return []
    try:
        lines = justfile.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        errors.append({"file": "Justfile", "kind": "io", "message": str(exc)})
        return []
    recipes: list[str] = []
    for line in lines:
        if not line or line[0] in (" ", "\t", "#", "["):
            continue
        raw = line.lstrip("@")
        m = _RECIPE_RE.match(raw)
        if m and m.group(1) not in _JUST_KEYWORDS:
            recipes.append(m.group(1))
    return recipes[:100]


def _parse_yaml_section_keys(text: str, section: str) -> list[str]:
    """Return first-level child keys under a YAML top-level `section:` key."""
    in_section = False
    keys: list[str] = []
    for line in text.splitlines():
        rstripped = line.rstrip()
        if not rstripped or rstripped.lstrip().startswith("#"):
            continue
        if not rstripped[0].isspace():
            in_section = rstripped == f"{section}:"
        elif in_section:
            m = _YAML_CHILD_RE.match(rstripped)
            if m:
                keys.append(m.group(1))
    return keys


def extract_taskfile_tasks(root: Path, errors: list[dict[str, str]]) -> list[str]:
    for name in ("Taskfile.yml", "Taskfile.yaml", "taskfile.yml", "taskfile.yaml"):
        candidate = root / name
        if candidate.exists():
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                errors.append({"file": name, "kind": "io", "message": str(exc)})
                return []
            return _parse_yaml_section_keys(text, "tasks")[:100]
    return []


def extract_docker_services(root: Path, errors: list[dict[str, str]]) -> list[str]:
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        candidate = root / name
        if candidate.exists():
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                errors.append({"file": name, "kind": "io", "message": str(exc)})
                return []
            return _parse_yaml_section_keys(text, "services")[:100]
    return []


def extract_workspace_packages(root: Path, errors: list[dict[str, str]]) -> list[str]:
    pkg = root / "package.json"
    if not pkg.exists():
        return []
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        errors.append({"file": "package.json", "kind": "json_parse", "message": str(exc)})
        return []
    ws = data.get("workspaces")
    if isinstance(ws, list):
        return [str(p) for p in ws][:100]
    if isinstance(ws, dict):
        return [str(p) for p in ws.get("packages", [])][:100]
    return []
